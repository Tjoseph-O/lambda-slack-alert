cat > scripts/setup-secrets.sh << 'EOF'
#!/bin/bash

STAGE=${1:-dev}
echo "🔒 Setting up secrets for stage: $STAGE"

# Prompt for MongoDB credentials securely
echo "Enter MongoDB connection string (input will be hidden):"
read -s MONGODB_URI

echo "Enter MongoDB database name:"
read MONGODB_DATABASE

echo "Enter Slack webhook URL (input will be hidden):"
read -s SLACK_WEBHOOK

# Create/update Parameter Store parameters
echo "📝 Creating MongoDB URI parameter..."
aws ssm put-parameter \
    --name "/power-alerts/$STAGE/mongodb/uri" \
    --value "$MONGODB_URI" \
    --type "SecureString" \
    --overwrite \
    --description "MongoDB connection URI for power alerts" \
    --region us-east-1

echo "📝 Creating MongoDB database parameter..."
aws ssm put-parameter \
    --name "/power-alerts/$STAGE/mongodb/database" \
    --value "$MONGODB_DATABASE" \
    --type "String" \
    --overwrite \
    --description "MongoDB database name for power alerts" \
    --region us-east-1

echo "📝 Creating Slack webhook secret..."
aws secretsmanager create-secret \
    --name "power-alerts/$STAGE/slack-webhook" \
    --description "Slack webhook URL for power transaction alerts" \
    --secret-string "{\"webhook_url\":\"$SLACK_WEBHOOK\"}" \
    --region us-east-1 2>/dev/null || \
aws secretsmanager update-secret \
    --secret-id "power-alerts/$STAGE/slack-webhook" \
    --secret-string "{\"webhook_url\":\"$SLACK_WEBHOOK\"}" \
    --region us-east-1

echo "✅ All secrets have been securely stored!"
echo "🔍 You can verify with:"
echo "  aws ssm describe-parameters --filters Key=Name,Values=/power-alerts/$STAGE/"

# Clear variables from memory
unset MONGODB_URI
unset MONGODB_DATABASE
unset SLACK_WEBHOOK


# Make script executable
chmod +x scripts/setup-secrets.sh