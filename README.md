# MongoDB Smart Home Data Management

This repository contains a Flask application for managing and visualizing smart home sensor data with MongoDB.

## Prerequisites

- Python 3.6+
- MongoDB Atlas account
- Git

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mongodb-smart-home.git
   cd mongodb-smart-home
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Run the setup script:
   ```bash
   python setup.py
   ```
   This will:
   - Install all required Python packages
   - Create a `.secrets` file with your MongoDB credentials
   - Export the credentials to your environment

4. Configure MongoDB Atlas:
   - Log in to your MongoDB Atlas account
   - Create a new cluster if you don't have one
   - Add your IP address to the IP whitelist
   - Create a database user with read/write permissions
   - Get your connection string from the "Connect" button

5. Run the application:
   ```bash
   ./run_app.sh
   ```
   The application will start on http://localhost:5000

## Environment Setup

The application uses environment variables for configuration. These are managed through the `.secrets` file:

```bash
MONGODB_URI=your_cluster.mongodb.net
MONGODB_USERNAME=your_username
MONGODB_PASSWORD=your_password
```

To update your credentials:
1. Delete the existing `.secrets` file
2. Run `python setup.py` again
3. Enter your new credentials when prompted

## Queryable Encryption Setup

To enable Queryable Encryption in your application:

1. Install the required dependencies:
   ```bash
   pip install pymongo[encryption]
   ```

2. Install libmongocrypt:
   ```bash
   # For macOS
   brew install libmongocrypt
   
   # For Linux
   sudo apt-get install libmongocrypt
   ```

3. Create a Customer Master Key (CMK):
   - Follow the [MongoDB documentation](https://www.mongodb.com/docs/manual/core/queryable-encryption/overview-enable-qe/) to set up your CMK
   - Store your CMK credentials securely

4. Configure your application:
   - Update the encryption schema in `qe_utils.py`
   - Set up your encryption client using the provided helper functions
   - Ensure your MongoDB Atlas cluster supports Queryable Encryption

5. Test the encryption:
   - Use the `/qe_demo` endpoint to test encrypted queries
   - Verify that sensitive data is properly encrypted

For detailed instructions, refer to the [MongoDB Queryable Encryption documentation](https://www.mongodb.com/docs/manual/core/queryable-encryption/overview-enable-qe/).

## Application Features

- Real-time electricity usage visualization
- 5-minute interval data aggregation
- Time series data storage in MongoDB
- Queryable encryption support for sensitive data

## Data Structure

The application stores sensor readings with the following structure:
```json
{
  "deviceId": "string",
  "brand": "string",
  "model": "string",
  "device_name": "string",
  "category": "string",
  "current_usage": number,
  "temperature": number,
  "pressure": number,
  "device_state": "string",
  "battery_level": number,
  "Timestamp": ISODate
}
```

## Troubleshooting

If you encounter connection issues:

1. Verify your MongoDB credentials:
   ```bash
   env | grep MONGODB
   ```

2. Check MongoDB Atlas:
   - Ensure your IP is whitelisted
   - Verify your database user has correct permissions
   - Confirm your cluster is running

3. Check the application logs:
   ```bash
   ./run_app.sh
   ```

4. Common errors:
   - "Connection refused": Check your MongoDB URI and credentials
   - "Invalid URI host": Verify your MongoDB URI format
   - "Authentication failed": Check your username and password

## Security Notes

- The `.secrets` file contains sensitive credentials
- Add `.secrets` to your `.gitignore` file
- Never commit credentials to version control
- Use strong passwords for your MongoDB user
- For Queryable Encryption, ensure your CMK is stored securely
- Regularly rotate your encryption keys

## License

This project is licensed under the MIT License - see the LICENSE file for details.
