import json
import os
import boto3
from datetime import datetime, timedelta
from pymongo import MongoClient
import requests
from bson import ObjectId

mongodb_client = None
database = None

def lambda_handler(event, context):
    """
    Main Lambda function for power transaction revenue alerts
    Triggered 4 times daily: 12AM, 6AM, 12PM, 6PM
    """
    try:
        # Initialize MongoDB connection
        init_mongodb_connection()
        
        # Get current time and determine reporting period
        current_time = datetime.utcnow()
        start_time, end_time, period_name = get_report_period(current_time)
        
        print(f"📊 Generating report for: {period_name}")
        print(f"⏰ Time range: {start_time} to {end_time}")
        
        # Query power transaction data
        revenue_data = get_power_transaction_revenue(start_time, end_time)
        
        # Send Slack alert
        send_revenue_alert(revenue_data, period_name, start_time, end_time)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Power transaction alert sent successfully',
                'period': period_name,
                'total_revenue': float(revenue_data['total_amount']),
                'transaction_count': revenue_data['total_transactions']
            })
        }
        
    except Exception as e:
        error_msg = f"Error in power transaction alert: {str(e)}"
        print(error_msg)
        send_error_alert(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def init_mongodb_connection():
    """
    Initialize MongoDB connection with connection reuse
    """
    global mongodb_client, database
    
    if mongodb_client is None:
        # Get connection details from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(
            SecretId='transaction-alerts/mongodb-credentials'
        )
        secrets = json.loads(secret_response['SecretString'])
        
        # Create MongoDB client
        mongodb_client = MongoClient(
            secrets['mongodb_uri'],
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
            maxPoolSize=5,
            retryWrites=True
        )
        
        # Connect to your specific database
        database = mongodb_client['bill_vending']
        
        print("✅ MongoDB connection initialized")

def get_report_period(current_time):
    """
    Calculate the 6-hour reporting period based on current trigger time
    """
    hour = current_time.hour
    
    if hour == 0:  # 12:00 AM trigger
        # Report previous day 18:01 to 23:59
        end_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Evening Period (6:01 PM - 11:59 PM)"
        
    elif hour == 6:  # 6:00 AM trigger
        # Report 00:01 to 05:59
        end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Night Period (12:01 AM - 5:59 AM)"
        
    elif hour == 12:  # 12:00 PM trigger
        # Report 06:01 to 11:59
        end_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Morning Period (6:01 AM - 11:59 AM)"
        
    elif hour == 18:  # 6:00 PM trigger
        # Report 12:01 to 17:59
        end_time = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Afternoon Period (12:01 PM - 5:59 PM)"
    
    else:
        # Fallback for testing or manual triggers
        end_time = current_time
        start_time = end_time - timedelta(hours=6)
        period_name = f"Last 6 Hours (ending {current_time.strftime('%H:%M')})"
    
    return start_time, end_time, period_name

def get_power_transaction_revenue(start_time, end_time):
    """
    Query MongoDB for power transaction revenue
    Returns: Total amount + breakdown by utility provider
    """
    collection = database['power_transaction_items']
    
    # Simplified aggregation pipeline
    pipeline = [
        # Match transactions in time range and successful status
        {
            '$match': {
                'createdAt': {
                    '$gte': start_time,
                    '$lte': end_time
                },
                'status': 'fulfilled',  # Only successful transactions
                'amount': {'$exists': True, '$ne': ''}
            }
        },
        # Convert amount string to number
        {
            '$addFields': {
                'amount_numeric': {
                    '$toDouble': {
                        '$cond': {
                            'if': {'$eq': [{'$type': '$amount'}, 'string']},
                            'then': '$amount',
                            'else': {'$toString': '$amount'}
                        }
                    }
                }
            }
        },
        # Create two separate groups: total and by utility
        {
            '$facet': {
                'total': [
                    {
                        '$group': {
                            '_id': None,
                            'total_amount': {'$sum': '$amount_numeric'},
                            'total_transactions': {'$sum': 1}
                        }
                    }
                ],
                'by_utility': [
                    {
                        '$group': {
                            '_id': '$util',
                            'amount': {'$sum': '$amount_numeric'},
                            'count': {'$sum': 1}
                        }
                    },
                    {
                        '$sort': {'amount': -1}  # Sort by highest amount first
                    }
                ]
            }
        }
    ]
    
    # Execute aggregation
    result = list(collection.aggregate(pipeline))
    
    if result and len(result) > 0:
        data = result[0]
        
        # Extract total
        total_data = data.get('total', [{}])[0]
        total_amount = float(total_data.get('total_amount', 0))
        total_transactions = int(total_data.get('total_transactions', 0))
        
        # Extract utility breakdown
        utility_breakdown = []
        for util_data in data.get('by_utility', []):
            utility_breakdown.append({
                'util': util_data['_id'],
                'amount': float(util_data['amount']),
                'transactions': int(util_data['count'])
            })
        
        return {
            'total_amount': total_amount,
            'total_transactions': total_transactions,
            'utility_breakdown': utility_breakdown
        }
    else:
        return {
            'total_amount': 0.0,
            'total_transactions': 0,
            'utility_breakdown': []
        }

def send_revenue_alert(revenue_data, period_name, start_time, end_time):
    """
    Send simplified revenue alert to Slack
    Format: 1) Total amount, 2) Breakdown by utility
    """
    # Get Slack webhook URL from Secrets Manager
    secrets_client = boto3.client('secretsmanager')
    secret_response = secrets_client.get_secret_value(
        SecretId='transaction-alerts/slack-webhook'
    )
    secrets = json.loads(secret_response['SecretString'])
    webhook_url = secrets['webhook_url']
    
    # Format utility breakdown
    utility_text = ""
    if revenue_data['utility_breakdown']:
        utility_lines = []
        for util_data in revenue_data['utility_breakdown']:
            utility_lines.append(
                f"• *{util_data['util']}*: ₦{util_data['amount']:,.2f} ({util_data['transactions']} transactions)"
            )
        utility_text = "\n".join(utility_lines)
    else:
        utility_text = "No transactions found for this period"
    
    # Format time period for display
    time_display = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} UTC on {start_time.strftime('%Y-%m-%d')}"
    
    # Create simplified Slack message
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚡ Power Transaction Revenue Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📅 Period:* {period_name}\n*🕐 Time:* {time_display}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💰 Total Revenue Generated:*\n₦{revenue_data['total_amount']:,.2f}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn", 
                    "text": f"*📊 Total Transactions:* {revenue_data['total_transactions']:,}"
                }
            }
        ]
    }
    
    # Add utility breakdown if there are transactions
    if revenue_data['total_transactions'] > 0:
        message["blocks"].extend([
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🏢 Revenue Breakdown by Utility:*\n{utility_text}"
                }
            }
        ])
    
    # Send to Slack
    response = requests.post(
        webhook_url,
        json=message,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"Slack API error: {response.status_code} - {response.text}")
    
    print(f"✅ Revenue alert sent successfully!")
    print(f"💰 Total Revenue: ₦{revenue_data['total_amount']:,.2f}")
    print(f"📊 Transactions: {revenue_data['total_transactions']}")
    for util_data in revenue_data['utility_breakdown']:
        print(f"   {util_data['util']}: ₦{util_data['amount']:,.2f}")

def send_error_alert(error_message):
    """
    Send error notification to Slack
    """
    try:
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(
            SecretId='transaction-alerts/slack-webhook'
        )
        secrets = json.loads(secret_response['SecretString'])
        webhook_url = secrets['webhook_url']
        
        error_msg = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Power Transaction Alert System Error"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:* {error_message}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    }
                }
            ]
        }
        
        requests.post(webhook_url, json=error_msg, timeout=30)
        print("Error alert sent to Slack")
    except Exception as e:
        print(f"Failed to send error alert: {str(e)}")

# For testing purposes
def test_locally():
    """
    Test function locally with sample time periods
    """
    # Test with current time
    current_time = datetime.utcnow()
    start_time, end_time, period_name = get_report_period(current_time)
    
    print(f"Test period: {period_name}")
    print(f"Start: {start_time}")
    print(f"End: {end_time}")

if __name__ == "__main__":
    test_locally()