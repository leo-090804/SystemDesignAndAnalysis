from motor.motor_asyncio import AsyncIOMotorClient
import logging

MONGODB_CONNECTION_STRING = (
    "mongodb+srv://22024556:LeoLincoln9804@leo.vve8qrr.mongodb.net/"
)
MONGODB_DATABASE_NAME = "school_exchange"

logger = logging.getLogger(__name__)

class Database:
    client = None
    db = None
    is_closing = False

    @classmethod
    async def connect_to_database(cls):
        if cls.client is None or cls.is_closing:
            try:
                logger.info("Connecting to MongoDB...")
                cls.client = AsyncIOMotorClient(MONGODB_CONNECTION_STRING)
                cls.db = cls.client[MONGODB_DATABASE_NAME]
                cls.is_closing = False
                logger.info("Connected to MongoDB successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
                raise
        return cls.db

    @classmethod
    async def close_database_connection(cls):
        if cls.client and not cls.is_closing:
            cls.is_closing = True
            logger.info("Closing MongoDB connection...")
            cls.client.close()
            logger.info("MongoDB connection closed")

    @classmethod
    async def get_db(cls):
        """Safe method to get database connection, reconnecting if necessary"""
        if cls.client is None or cls.is_closing:
            await cls.connect_to_database()
        return cls.db
