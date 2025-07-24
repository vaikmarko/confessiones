#!/usr/bin/env python3
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting application...")
    
    # Import the app
    from app import app
    
    # Get port from environment
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting Flask app on port {port}")
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
    
except Exception as e:
    logger.error(f"Failed to start application: {e}")
    sys.exit(1) 