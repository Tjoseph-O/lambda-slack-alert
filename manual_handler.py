
import json
from lambda_function import lambda_handler as main_handler, test_locally

def lambda_handler(event, context):
    """Manual handler for testing and on-demand checks"""
    
    check_type = event.get('check_type', 'normal')
    
    if check_type == 'test':
        try:
            print("🧪 Running connectivity test...")
            test_locally()
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Test completed successfully',
                    'type': 'connectivity_test'
                })
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e),
                    'message': 'Test failed'
                })
            }
    
    elif check_type == 'force_run':
        print("🔄 Running forced revenue check...")
        return main_handler(event, context)
    
    else:
        print("📊 Running normal revenue check...")
        return main_handler(event, context)
