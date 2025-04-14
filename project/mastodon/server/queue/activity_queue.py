"""
Activity Queue Implementation

This module implements the RabbitMQ-based queue system for ActivityPub activities.
"""

import json
import logging
from typing import Dict, Optional, Callable
import pika
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActivityQueue:
    """Handles queuing and processing of outgoing ActivityPub activities."""
    
    def __init__(self, rabbitmq_url: str = "amqp://localhost"):
        """
        Initialize the activity queue.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
        """
        self.connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        self.channel = self.connection.channel()
        
        # Declare queues
        self.channel.queue_declare(queue='activitypub_outbox', durable=True)
        self.channel.queue_declare(queue='activitypub_processing', durable=True)
        self.channel.queue_declare(queue='activitypub_failed', durable=True)
        
        # Set QoS to ensure fair distribution
        self.channel.basic_qos(prefetch_count=1)
        
    def enqueue_activity(self, activity: Dict) -> bool:
        """
        Add an activity to the outbox queue.
        
        Args:
            activity: Activity to queue
            
        Returns:
            bool: True if successfully queued
        """
        try:
            # Add metadata
            activity['queued_at'] = datetime.utcnow().isoformat()
            activity['retry_count'] = 0
            
            # Publish to outbox queue
            self.channel.basic_publish(
                exchange='',
                routing_key='activitypub_outbox',
                body=json.dumps(activity),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Queued activity {activity.get('id', 'unknown')} for delivery")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue activity: {e}")
            return False
            
    def start_processing(self, callback: Callable[[Dict], bool]):
        """
        Start processing activities from the queue.
        
        Args:
            callback: Function to process each activity
        """
        def process_message(ch, method, properties, body):
            try:
                activity = json.loads(body)
                logger.info(f"Processing activity {activity.get('id', 'unknown')}")
                
                # Move to processing queue
                ch.basic_publish(
                    exchange='',
                    routing_key='activitypub_processing',
                    body=body,
                    properties=properties
                )
                
                # Process the activity
                success = callback(activity)
                
                if success:
                    # Acknowledge the message
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"Successfully processed activity {activity.get('id', 'unknown')}")
                else:
                    # Move to failed queue if processing failed
                    ch.basic_publish(
                        exchange='',
                        routing_key='activitypub_failed',
                        body=body,
                        properties=properties
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.error(f"Failed to process activity {activity.get('id', 'unknown')}")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Move to failed queue
                ch.basic_publish(
                    exchange='',
                    routing_key='activitypub_failed',
                    body=body,
                    properties=properties
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
        # Start consuming from outbox queue
        self.channel.basic_consume(
            queue='activitypub_outbox',
            on_message_callback=process_message
        )
        
        logger.info("Started processing activities from outbox queue")
        self.channel.start_consuming()
        
    def retry_failed_activities(self) -> int:
        """
        Retry failed activities that haven't exceeded retry limit.
        
        Returns:
            int: Number of activities retried
        """
        try:
            retried = 0
            
            # Get all messages from failed queue
            while True:
                method_frame, header_frame, body = self.channel.basic_get(
                    queue='activitypub_failed',
                    auto_ack=False
                )
                
                if method_frame is None:
                    break
                    
                activity = json.loads(body)
                retry_count = activity.get('retry_count', 0)
                
                if retry_count < 3:  # Max 3 retries
                    activity['retry_count'] = retry_count + 1
                    activity['last_retry'] = datetime.utcnow().isoformat()
                    
                    # Move back to outbox queue
                    self.channel.basic_publish(
                        exchange='',
                        routing_key='activitypub_outbox',
                        body=json.dumps(activity),
                        properties=pika.BasicProperties(
                            delivery_mode=2,
                            content_type='application/json'
                        )
                    )
                    retried += 1
                    
                # Acknowledge the message from failed queue
                self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                
            return retried
            
        except Exception as e:
            logger.error(f"Failed to retry activities: {e}")
            return 0
            
    def close(self):
        """Close the RabbitMQ connection."""
        self.connection.close() 