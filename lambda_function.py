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
    
    try:
        
        init_mongodb_connection()
        
        
        current_time = datetime.utcnow()
        start_time, end_time, period_name = get_report_period(current_time)
        
        print(f"📊 Generating report for: {period_name}")
        print(f"⏰ Time range: {start_time} to {end_time}")
        
        
        revenue_data = get_power_transaction_revenue(start_time, end_time)
        
        
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
    
    global mongodb_client, database
    
    if mongodb_client is None:
        
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(
            SecretId='transaction-alerts/mongodb-credentials'
        )
        secrets = json.loads(secret_response['SecretString'])
        
        
        mongodb_client = MongoClient(
            secrets['mongodb_uri'],
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
            maxPoolSize=5,
            retryWrites=True
        )
        
        
        database = mongodb_client['bill_vending']
        
        print("✅ MongoDB connection initialized")

def get_report_period(current_time):
    hour = current_time.hour
    
    if hour == 0:
        end_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Evening Period (6:01 PM - 11:59 PM)"
        
    elif hour == 6:
        end_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Night Period (12:01 AM - 5:59 AM)"
        
    elif hour == 12:
        end_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Morning Period (6:01 AM - 11:59 AM)"
        
    elif hour == 18:
        end_time = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
        start_time = (end_time - timedelta(hours=6)).replace(minute=1)
        end_time = end_time.replace(minute=59, second=59) - timedelta(microseconds=1)
        period_name = "Afternoon Period (12:01 PM - 5:59 PM)"
    
    else:
        end_time = current_time
        start_time = end_time - timedelta(hours=6)
        period_name = f"Last 6 Hours (ending {current_time.strftime('%H:%M')})"
    
    print(f"📅 Period calculation - Hour: {hour}, Start: {start_time}, End: {end_time}")
    return start_time, end_time, period_name

def get_power_transaction_revenue(start_time, end_time):
    collection = database['power_transaction_items']
    
    print(f"🔍 Querying transactions from {start_time} to {end_time}")
    
    try:
        pipeline = [
            {
                '$match': {
                    'createdAt': {
                        '$gte': start_time,
                        '$lte': end_time
                    },
                    'status': 'fulfilled',
                    'amount': {'$exists': True, '$ne': ''}
                }
            },
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
                            '$sort': {'amount': -1}
                        }
                    ]
                }
            }
        ]
        
        result = list(collection.aggregate(pipeline))
        print(f"📊 Raw aggregation result: {result}")
        
        if not result:
            print("⚠️ No result from aggregation pipeline")
            return {
                'total_amount': 0.0,
                'total_transactions': 0,
                'utility_breakdown': []
            }
        
        data = result[0]
        print(f"📊 Processed data structure: {data}")
        
        total_data_list = data.get('total', [])
        if not total_data_list:
            print("⚠️ No total data found")
            total_amount = 0.0
            total_transactions = 0
        else:
            total_data = total_data_list[0]
            total_amount = float(total_data.get('total_amount', 0))
            total_transactions = int(total_data.get('total_transactions', 0))
        
        utility_breakdown = []
        by_utility_list = data.get('by_utility', [])
        for util_data in by_utility_list:
            if util_data.get('_id'):
                utility_breakdown.append({
                    'util': util_data['_id'],
                    'amount': float(util_data['amount']),
                    'transactions': int(util_data['count'])
                })
        
        result_summary = {
            'total_amount': total_amount,
            'total_transactions': total_transactions,
            'utility_breakdown': utility_breakdown
        }
        
        print(f"📊 Final result summary: {result_summary}")
        return result_summary
        
    except Exception as e:
        print(f"❌ Error in aggregation: {str(e)}")
        print(f"📊 Falling back to simple count query")
        
        try:
            simple_count = collection.count_documents({
                'createdAt': {
                    '$gte': start_time,
                    '$lte': end_time
                },
                'status': 'fulfilled'
            })
            print(f"📊 Simple count result: {simple_count} transactions")
            
            return {
                'total_amount': 0.0,
                'total_transactions': simple_count,
                'utility_breakdown': []
            }
        except Exception as e2:
            print(f"❌ Error in simple count: {str(e2)}")
            return {
                'total_amount': 0.0,
                'total_transactions': 0,
                'utility_breakdown': []
            }

def send_revenue_alert(revenue_data, period_name, start_time, end_time):
    try:
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(
            SecretId='transaction-alerts/slack-webhook'
        )
        
        secret_string = secret_response['SecretString']
        print(f"🔐 Raw secret string: {secret_string[:50]}...")
        
        try:
            secrets = json.loads(secret_string)
            webhook_url = secrets['webhook_url']
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            webhook_url = secret_string.strip().strip('"')
            print(f"🔗 Using raw webhook URL")
        
        print(f"🔗 Webhook URL length: {len(webhook_url)}")
        
    except Exception as e:
        print(f"❌ Error getting webhook URL: {e}")
        return
    
    time_display = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} UTC on {start_time.strftime('%Y-%m-%d')}"
    
    if revenue_data['total_transactions'] == 0:
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
                        "text": "📭 *No new transactions yet*\n\nNo power transactions were processed during this period."
                    }
                }
            ]
        }
    else:
        utility_text = ""
        if revenue_data['utility_breakdown']:
            utility_lines = []
            for util_data in revenue_data['utility_breakdown']:
                utility_lines.append(
                    f"• *{util_data['util']}*: ₦{util_data['amount']:,.2f} ({util_data['transactions']} transactions)"
                )
            utility_text = "\n".join(utility_lines)
        
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
                },
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
            ]
        }
    
    try:
        print(f"📤 Sending message to Slack...")
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📤 Slack response status: {response.status_code}")
        print(f"📤 Slack response: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"Slack API error: {response.status_code} - {response.text}")
        
        if revenue_data['total_transactions'] == 0:
            print("📭 No transactions alert sent successfully!")
        else:
            print(f"✅ Revenue alert sent successfully!")
            print(f"💰 Total Revenue: ₦{revenue_data['total_amount']:,.2f}")
            print(f"📊 Transactions: {revenue_data['total_transactions']}")
            for util_data in revenue_data['utility_breakdown']:
                print(f"   {util_data['util']}: ₦{util_data['amount']:,.2f}")
                
    except Exception as e:
        print(f"❌ Error sending to Slack: {e}")
        raise e

def send_error_alert(error_message):
    try:
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(
            SecretId='transaction-alerts/slack-webhook'
        )
        secrets = json.loads(secret_response['SecretString'])
        webhook_url = secrets['webhook_url']
        
        clean_error_msg = str(error_message).replace('"', "'").replace('\n', ' ')
        
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
                        "text": f"*Error:* {clean_error_msg}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    }
                }
            ]
        }
        
        requests.post(webhook_url, json=error_msg, timeout=30)
        print("Error alert sent to Slack")
    except Exception as e:
        print(f"Failed to send error alert: {str(e)}")


def test_locally():
    
    
    current_time = datetime.utcnow()
    start_time, end_time, period_name = get_report_period(current_time)
    
    print(f"Test period: {period_name}")
    print(f"Start: {start_time}")
    print(f"End: {end_time}")

if __name__ == "__main__":
    test_locally()