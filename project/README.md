# Opencamp Week 2 Assignment

proof of concept for an activitypub server setup where we can upload 1 text-based post

## Core ActivityPub architecture:

- Actor: fundamental primitive component of the social web (think like traditional 'account', but buffed)

- Defines a core 'distributed event log' architectural model for the open social web: to model any social interaction, use an extensible Object, wrapped in an Activity.

- Defines a Server-to-Server (S2S) protocol for distributing Objects and Activities to interested parties

- Defines a Client-to-Server (C2S) protocol for client software to interact with Actors and their data

- Uses the ActivityStreams 2 (AS2) core data model to describesome commonly used social web activities, and the corresponding ActivityStreams Vocabulary that describes common extensions to AS2

- Uses Linked Data (JSON-LD) as decentralized mechanism for publishing data model extensions
