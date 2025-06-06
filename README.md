

# ⚡ Power Transaction Revenue Alert System

Automated Slack notifications for power transaction revenue reports every 6 hours.

## 🎯 Overview

This system automatically queries MongoDB for power transaction data, calculates revenue by utility provider, and sends formatted reports to Slack. It runs on AWS Lambda with EventBridge scheduling.

## 🏗️ Architecture

```
EventBridge Schedule (every 6 hours)
         ↓
    AWS Lambda Function
         ↓
    MongoDB Query (power_transaction_items)
         ↓
    Revenue Calculation & Formatting
         ↓
    Slack Webhook Notification
```

## ⏰ Schedule

Automated alerts are sent at:
- **12:00 AM** - Reports evening period (6:01 PM - 11:59 PM)
- **6:00 AM** - Reports night period (12:01 AM - 5:59 AM)
- **12:00 PM** - Reports morning period (6:01 AM - 11:59 AM)
- **6:00 PM** - Reports afternoon period (12:01 PM - 5:59 PM)

## 📊 Features

### ✅ Revenue Reporting
- Total revenue calculation for 6-hour periods
- Breakdown by utility provider (IKEDC, EKEDC, etc.)
- Transaction count by utility
- Formatted currency display (₦)

### ✅ Smart Notifications
- **With Transactions**: Detailed revenue breakdown
- **No Transactions**: "No new transactions yet" message
- **Errors**: Automatic error alerts to Slack

### ✅ Data Processing
- Handles string and numeric amount formats
- Filters for successful transactions only (`status: 'fulfilled'`)
- UTC timezone handling
- Robust error handling with fallbacks

## 📱 Sample Slack Output

### With Transactions
```
⚡ Power Transaction Revenue Report

📅 Period: Afternoon Period (12:01 PM - 5:59 PM)
🕐 Time: 12:01 - 18:59 UTC on 2025-05-29

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Total Revenue Generated:
₦45,750.00

📊 Total Transactions: 23

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 Revenue Breakdown by Utility:
• IKEDC: ₦25,500.00 (14 transactions)
• EKEDC: ₦12,750.00 (6 transactions)
• AEDC: ₦7,500.00 (3 transactions)
```

### No Transactions
```
⚡ Power Transaction Revenue Report

📅 Period: Afternoon Period (12:01 PM - 5:59 PM)
🕐 Time: 12:01 - 18:59 UTC on 2025-05-29

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📭 No new transactions yet

No power transactions were processed during this period.
```

## 🛠️ Technical Implementation

### MongoDB Query
- **Collection**: `power_transaction_items`
- **Filters**: Date range, `status: 'fulfilled'`, valid amounts
- **Aggregation**: Uses `$facet` for total and utility breakdown
- **Fallback**: Simple count query if aggregation fails

### Data Processing
- **Amount Conversion**: Handles both string and numeric formats
- **Timezone**: All calculations in UTC
- **Sorting**: Utilities ordered by revenue (highest first)

### Error Handling
- MongoDB connection failures
- Invalid data formats
- Slack webhook errors
- Comprehensive logging for debugging

## 🚀 Deployment

### Prerequisites
- AWS Lambda function
- MongoDB Atlas connection
- Slack webhook URL
- EventBridge schedule rule

### Dependencies
```bash
pip install pymongo requests
```

### AWS Resources
1. **Lambda Function**: `power-transaction-revenue-alerts`
2. **IAM Role**: Lambda execution role with Secrets Manager access
3. **Secrets Manager**: 
   - `transaction-alerts/mongodb-connection`
   - `transaction-alerts/slack-webhook`
4. **EventBridge Rule**: Scheduled expression for 6-hour intervals

### Environment Setup
1. Deploy Lambda function with dependencies
2. Configure MongoDB connection string in Secrets Manager
3. Configure Slack webhook URL in Secrets Manager
4. Set up EventBridge rule for scheduling
5. Test function execution

## 🔧 Configuration

### MongoDB Secret Format
```json
{
  "connection_string": "mongodb+srv://username:password@cluster.mongodb.net/database"
}
```

### Slack Webhook Secret Format
```json
{
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

## 📈 Business Value

### Automation Benefits
- **Time Savings**: Eliminates manual reporting
- **Consistency**: Reports generated every 6 hours without fail
- **Real-time Insights**: Immediate visibility into revenue trends
- **Error Reduction**: Automated calculations reduce human error

### Revenue Tracking
- **Period Comparison**: Track performance across different time periods
- **Utility Analysis**: Identify top-performing utility providers
- **Transaction Volume**: Monitor business activity levels
- **Trend Identification**: Spot patterns in revenue generation

## 🧪 Testing

### Manual Test
```bash
# In AWS Lambda Console
1. Click "Test" button
2. Use default test event
3. Check CloudWatch logs for execution details
4. Verify Slack notification
```

### Expected Test Results
- **Success Response**: HTTP 200 with JSON body
- **CloudWatch Logs**: Detailed execution steps
- **Slack Message**: Alert appears in configured channel

### Debug Information
Function provides detailed logging:
- MongoDB connection status
- Query time ranges
- Raw aggregation results
- Slack webhook responses

## 🔍 Monitoring

### CloudWatch Metrics
- Function duration
- Error rates
- Invocation count
- Memory usage

### Log Analysis
- Successful executions
- MongoDB connection issues
- Slack delivery failures
- Error patterns

## 🛡️ Security

### Best Practices
- ✅ Secrets stored in AWS Secrets Manager
- ✅ Minimal IAM permissions
- ✅ No hardcoded credentials
- ✅ Encrypted connections to MongoDB
- ✅ HTTPS webhooks to Slack

### Access Control
- Lambda execution role with least privilege
- Secrets Manager access only for required secrets
- VPC configuration if needed for MongoDB

## 📝 Maintenance

### Regular Tasks
- Monitor CloudWatch logs for errors
- Verify Slack notifications are being received
- Check MongoDB connection health
- Update dependencies as needed

### Scaling Considerations
- Function timeout: Currently 30 seconds (sufficient for current load)
- Memory: 512 MB (optimized for MongoDB queries)
- Concurrency: Single execution per schedule (no overlap needed)

## 🤝 Contributing

### Code Standards
- Detailed logging for debugging
- Error handling for all external calls
- UTC timezone for all date operations
- Descriptive variable names
- Comprehensive documentation

### Testing Requirements
- Test with both transaction and no-transaction scenarios
- Verify Slack message formatting
- Validate MongoDB query accuracy
- Check error handling paths

---

**System Status**: ✅ Production Ready  
**Last Updated**: May 29, 2025  
**Deployment**: AWS Lambda (us-east-1)  
**Monitoring**: CloudWatch + Slack Alerts
