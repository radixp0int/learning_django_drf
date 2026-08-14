from django.urls import reverse
from rest_framework.test import APITestCase


class RouterBasenameTest(APITestCase):
    """
    miniapp and analytics both expose a Feedback viewset. Without explicit
    basenames the router derives 'feedback' for both, and the second
    registration silently wins every reverse lookup.
    """

    def test_miniapp_feedback_reverses_to_its_own_url(self):
        self.assertEqual(reverse('feedback-list'), '/api/feedback/')

    def test_analytics_feedback_reverses_to_its_own_url(self):
        self.assertEqual(reverse('analytics-feedback-list'), '/api/analytics/feedback/')

    def test_detail_routes_stay_distinct(self):
        self.assertEqual(reverse('feedback-detail', args=[1]), '/api/feedback/1/')
        self.assertEqual(
            reverse('analytics-feedback-detail', args=[1]), '/api/analytics/feedback/1/'
        )

    def test_api_root_links_feedback_to_miniapp(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['feedback'].endswith('/api/feedback/'))
