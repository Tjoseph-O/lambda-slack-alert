#!/bin/bash

# Production Secrets Setup Script for Power Alerts Lambda
# Usage: ./setup-prod-secrets.sh

STAGE="prod"
echo "🔒 Setting up PRODUCTION secrets for Power Alerts"
echo "================================================="


echo "Enter PRODUCTION MongoDB connection string (input will be hidden):"
read -s MONGODB_URI

echo "Enter PRODUCTION Slack webhook URL (input will be hidden):"
read -s SLACK_WEBHOOK

echo ""
echo "📝 Creating PRODUCTION secrets..."


echo "📝 Creating PRODUCTION Slack webhook secret..."
aws secretsmanager create-secret \
    --name "power-alerts/prod/slack-webhook" \
    --secret-string "{\"webhook_url\":\"$SLACK_WEBHOOK\"}" \
    --region us-east-1 2>/dev/null || \
aws secretsmanager update-secret \
    --secret-id "power-alerts/prod/slack-webhook" \
    --secret-string "{\"webhook_url\":\"$SLACK_WEBHOOK\"}" \
    --region us-east-1


echo "📝 Creating PRODUCTION MongoDB URI parameter..."
aws ssm put-parameter \
    --name "/power-alerts/prod/mongodb/uri" \
    --value "$MONGODB_URI" \
    --type "SecureString" \
    --overwrite \
    --region us-east-1


echo "📝 Creating PRODUCTION MongoDB database parameter..."
aws ssm put-parameter \
    --name "/power-alerts/prod/mongodb/database" \
    --value "bill_vending" \
    --type "String" \
    --overwrite \
    --region us-east-1

echo "✅ All PRODUCTION secrets have been securely stored!"
echo ""
echo "🔍 You can verify with:"
echo "  aws ssm describe-parameters --filters Key=Name,Values=/power-alerts/prod/"
echo "  aws secretsmanager describe-secret --secret-id power-alerts/prod/slack-webhook"


unset MONGODB_URI
unset SLACK_WEBHOOK

echo ""
echo "🚀 PRODUCTION secrets setup complete!"
echo "💡 Now you can deploy to production using your CI/CD pipeline or SAM deploy"