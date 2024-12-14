from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, start_http_server
import os

class Analytics:
    def __init__(self, property_id):
        self.property_id = property_id
        self.client = BetaAnalyticsDataClient()
        
        # Prometheus metrics
        self.page_views = Counter('page_views_total', 'Total page views', ['path'])
        self.response_time = Histogram('response_time_seconds', 'Response time in seconds')
        
        # Start Prometheus metrics server
        start_http_server(8000)

    def track_pageview(self, path, user_agent=None, ip=None):
        """Track a pageview in both GA4 and Prometheus"""
        self.page_views.labels(path=path).inc()

    @self.response_time.time()
    def get_pageviews(self, days=30):
        """Get pageview data from GA4"""
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=f"{days}daysAgo",
                    end_date="today"
                )],
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name="screenPageViews")]
            )
            response = self.client.run_report(request)
            
            return [{
                'path': row.dimension_values[0].value,
                'views': row.metric_values[0].value
            } for row in response.rows]
        except Exception as e:
            print(f"Error fetching GA4 data: {e}")
            return []

    def get_top_posts(self, limit=10):
        """Get top performing posts"""
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date="30daysAgo",
                    end_date="today"
                )],
                dimensions=[
                    Dimension(name="pagePath"),
                    Dimension(name="pageTitle")
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="engagementRate"),
                    Metric(name="averageSessionDuration")
                ]
            )
            response = self.client.run_report(request)
            
            return [{
                'path': row.dimension_values[0].value,
                'title': row.dimension_values[1].value,
                'views': int(row.metric_values[0].value),
                'engagement_rate': float(row.metric_values[1].value),
                'avg_duration': float(row.metric_values[2].value)
            } for row in response.rows[:limit]]
        except Exception as e:
            print(f"Error fetching top posts: {e}")
            return []

    def get_user_metrics(self, days=30):
        """Get user engagement metrics"""
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=f"{days}daysAgo",
                    end_date="today"
                )],
                metrics=[
                    Metric(name="totalUsers"),
                    Metric(name="newUsers"),
                    Metric(name="activeUsers"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate")
                ]
            )
            response = self.client.run_report(request)
            
            if response.rows:
                row = response.rows[0]
                return {
                    'total_users': int(row.metric_values[0].value),
                    'new_users': int(row.metric_values[1].value),
                    'active_users': int(row.metric_values[2].value),
                    'avg_session_duration': float(row.metric_values[3].value),
                    'bounce_rate': float(row.metric_values[4].value)
                }
            return None
        except Exception as e:
            print(f"Error fetching user metrics: {e}")
            return None

    def get_traffic_sources(self, days=30):
        """Get traffic source data"""
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=f"{days}daysAgo",
                    end_date="today"
                )],
                dimensions=[Dimension(name="sessionSource")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="engagementRate")
                ]
            )
            response = self.client.run_report(request)
            
            return [{
                'source': row.dimension_values[0].value,
                'sessions': int(row.metric_values[0].value),
                'engagement_rate': float(row.metric_values[1].value)
            } for row in response.rows]
        except Exception as e:
            print(f"Error fetching traffic sources: {e}")
            return []

# Initialize analytics
analytics = Analytics(os.getenv('GA4_PROPERTY_ID'))
