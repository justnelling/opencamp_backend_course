"""
ActivityPub Outbox Worker

This script runs as a separate process to handle the delivery of outgoing ActivityPub activities.
It consumes activities from the queue and delivers them to target servers.
"""

import os
import json
import logging
import requests
from typing import Dict
from .activity_queue import ActivityQueue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActivityWorker:
    """Worker for processing and delivering ActivityPub activities."""
    
    def __init__(self, rabbitmq_url: str = "amqp://localhost"):
        """
        Initialize the worker.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
        """
        self.queue = ActivityQueue(rabbitmq_url)
        
    def deliver_activity(self, activity: Dict) -> bool:
        """
        Deliver an activity to its target server.
        
        Args:
            activity: Activity to deliver
            
        Returns:
            bool: True if successfully delivered
        """
        try:
            # Get target server from activity
            target = activity.get('target')
            if not target:
                logger.error("Activity missing target server")
                return False
                
            # Prepare headers
            headers = {
                'Content-Type': 'application/activity+json',
                'User-Agent': 'Mastodon/3.5.3',
                # Add signature headers here when implemented
            }
            
            # Send POST request to target server's inbox
            response = requests.post(
                f"{target}/inbox",
                json=activity,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully delivered activity to {target}")
                return True
            else:
                logger.error(f"Failed to deliver activity: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error delivering activity: {e}")
            return False
            
    def run(self):
        """Start the worker."""
        try:
            logger.info("Starting ActivityPub outbox worker")
            
            # Start processing activities
            self.queue.start_processing(self.deliver_activity)
            
        except KeyboardInterrupt:
            logger.info("Shutting down worker")
        finally:
            self.queue.close()
            
def main():
    """Main entry point."""
    # Get RabbitMQ URL from environment or use default
    rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://localhost')
    
    # Create and run worker
    worker = ActivityWorker(rabbitmq_url)
    worker.run()
    
if __name__ == '__main__':
    main() 