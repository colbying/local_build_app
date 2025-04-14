# MongoDB Smart Home Data Management

This repository contains a Flask application for managing and visualizing smart home sensor data with MongoDB.

## Prerequisites

- Python 3.6+
- MongoDB Atlas account
- Git
- AWS account (for Queryable Encryption)

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

## Setup Scripts

### 1. Initial Setup (setup.py)

The `setup.py` script handles the initial application setup:

```bash
python setup.py
```

This script will:
- Install all required Python packages
- Create a `.secrets` file with your MongoDB credentials
- Export the credentials to your environment

If you need to update your MongoDB credentials:
1. Delete the existing `.secrets` file
2. Run `setup.py` again
3. Enter your new credentials when prompted

### 2. Queryable Encryption Setup (setup_queryable_encryption.py)

The `setup_queryable_encryption.py` script configures AWS credentials for Queryable Encryption:

```bash
python setup_queryable_encryption.py
```

This script will:
- Check for existing AWS credentials in `.secrets`
- If credentials exist, it will:
  - Display the existing credentials
  - Export them to the environment
  - Exit without prompting
- If credentials don't exist, it will:
  - Prompt for AWS credentials
  - Save them to `.secrets`
  - Export them to the environment

Required AWS credentials:
- AWS Access Key
- AWS Secret Key
- AWS KMS Key ID
- AWS KMS ARN

To update AWS credentials:
1. Delete the `.secrets` file
2. Run `setup.py` to set up MongoDB credentials
3. Run `setup_queryable_encryption.py` to set up AWS credentials

## Running the Application

After setting up both MongoDB and AWS credentials:

1. Start the application:
   ```bash
   ./run_app.sh
   ```
   The application will start on http://localhost:5000

2. Access the application:
   - Main dashboard: http://localhost:5000
   - Queryable Encryption demo: http://localhost:5000/qe_demo

## Environment Setup

The application uses environment variables for configuration. These are managed through the `.secrets` file:

```json
{
  "MONGODB_URI": "your_cluster.mongodb.net",
  "MONGODB_USERNAME": "your_username",
  "MONGODB_PASSWORD": "your_password",
  "AWS_ACCESS_KEY": "your_aws_access_key",
  "AWS_SECRET_KEY": "your_aws_secret_key",
  "AWS_KMS_KEY_ID": "your_kms_key_id",
  "AWS_KMS_ARN": "your_kms_arn"
}
```

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

2. Verify your AWS credentials:
   ```bash
   env | grep AWS
   ```

3. Check MongoDB Atlas:
   - Ensure your IP is whitelisted
   - Verify your database user has correct permissions
   - Confirm your cluster is running

4. Check the application logs:
   ```bash
   ./run_app.sh
   ```

5. Common errors:
   - "Connection refused": Check your MongoDB URI and credentials
   - "Invalid URI host": Verify your MongoDB URI format
   - "Authentication failed": Check your username and password
   - "KMS error": Verify your AWS credentials and KMS permissions

## Security Notes

- The `.secrets` file contains sensitive credentials
- Add `.secrets` to your `.gitignore` file
- Never commit credentials to version control
- Use strong passwords for your MongoDB user
- For Queryable Encryption, ensure your CMK is stored securely
- Regularly rotate your encryption keys

## License

This project is licensed under the MIT License - see the LICENSE file for details.
