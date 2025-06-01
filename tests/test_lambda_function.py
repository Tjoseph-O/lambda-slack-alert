import pytest
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path so we can import lambda_function
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda_function import get_report_period


class TestPowerAlertsLambda:
    
    def test_get_report_period_midnight(self):
        """Test period calculation for midnight (0:00)"""
        test_time = datetime(2025, 6, 1, 0, 0, 0)
        start_time, end_time, period_name = get_report_period(test_time)
        
        assert period_name == "Evening Period (6:01 PM - 11:59 PM)"
        assert start_time.hour == 18
        assert start_time.minute == 1
        assert end_time.hour == 23
        assert end_time.minute == 59
    
    def test_get_report_period_6am(self):
        """Test period calculation for 6 AM"""
        test_time = datetime(2025, 6, 1, 6, 0, 0)
        start_time, end_time, period_name = get_report_period(test_time)
        
        assert period_name == "Night Period (12:01 AM - 5:59 AM)"
        assert start_time.hour == 0
        assert start_time.minute == 1
        assert end_time.hour == 5
        assert end_time.minute == 59
    
    def test_get_report_period_noon(self):
        """Test period calculation for noon (12:00)"""
        test_time = datetime(2025, 6, 1, 12, 0, 0)
        start_time, end_time, period_name = get_report_period(test_time)
        
        assert period_name == "Morning Period (6:01 AM - 11:59 AM)"
        assert start_time.hour == 6
        assert start_time.minute == 1
        assert end_time.hour == 11
        assert end_time.minute == 59
    
    def test_get_report_period_6pm(self):
        """Test period calculation for 6 PM"""
        test_time = datetime(2025, 6, 1, 18, 0, 0)
        start_time, end_time, period_name = get_report_period(test_time)
        
        assert period_name == "Afternoon Period (12:01 PM - 5:59 PM)"
        assert start_time.hour == 12
        assert start_time.minute == 1
        assert end_time.hour == 17
        assert end_time.minute == 59
    
    def test_get_report_period_random_time(self):
        """Test period calculation for random time (not scheduled)"""
        test_time = datetime(2025, 6, 1, 15, 30, 0)
        start_time, end_time, period_name = get_report_period(test_time)
        
        assert "Last 6 Hours" in period_name
        assert "ending 15:30" in period_name
        
        # Should be exactly 6 hours apart
        time_diff = end_time - start_time
        assert time_diff == timedelta(hours=6)
    
    def test_period_calculations_are_consistent(self):
        """Test that period calculations are consistent"""
        test_times = [
            datetime(2025, 6, 1, 0, 0, 0),
            datetime(2025, 6, 1, 6, 0, 0),
            datetime(2025, 6, 1, 12, 0, 0),
            datetime(2025, 6, 1, 18, 0, 0),
        ]
        
        for test_time in test_times:
            start_time, end_time, period_name = get_report_period(test_time)
            
            # All periods should be valid
            assert start_time < end_time
            assert isinstance(period_name, str)
            assert len(period_name) > 0
            
            # Start time should be before test time
            assert start_time <= test_time
    
    def test_lambda_function_structure(self):
        """Test that lambda_function has required structure"""
        import lambda_function
        
        # Check required functions exist
        assert hasattr(lambda_function, 'lambda_handler')
        assert hasattr(lambda_function, 'get_report_period')
        assert hasattr(lambda_function, 'get_power_transaction_revenue')
        assert hasattr(lambda_function, 'send_revenue_alert')
        assert hasattr(lambda_function, 'send_error_alert')
        
        # Check functions are callable
        assert callable(lambda_function.lambda_handler)
        assert callable(lambda_function.get_report_period)
        assert callable(lambda_function.get_power_transaction_revenue)
        assert callable(lambda_function.send_revenue_alert)
        assert callable(lambda_function.send_error_alert)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])