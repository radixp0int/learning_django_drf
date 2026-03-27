from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.request import Request
from core.pagination import StandardResultsSetPagination
from django.utils import timezone
import json

class MockView:
    ordering = ['-created_at']

class PaginationTest(APITestCase):
    def test_standard_results_set_pagination_structure(self):
        pagination = StandardResultsSetPagination()
        factory = APIRequestFactory()
        request = factory.get('/?page=1&size=10')
        drf_request = Request(request)
        
        # Mocking the page object which DRF pagination expects
        class MockPaginator:
            count = 4
            num_pages = 1

        class MockPage:
            paginator = MockPaginator()
            number = 1
            def has_previous(self): return False
            def has_next(self): return False
            def start_index(self): return 1

        pagination.page = MockPage()
        pagination.request = drf_request
        
        # Add mock view to request context
        drf_request.parser_context = {'view': MockView()}
        
        data = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]
        response = pagination.get_paginated_response(data)
        
        self.assertEqual(response.status_code, 200)
        content = response.data
        
        self.assertTrue(content['success'])
        self.assertIn('timestamp', content)
        self.assertEqual(content['message'], 'Data retrieved successfully.')
        self.assertEqual(content['status'], 200)
        
        data_part = content['data']
        self.assertEqual(data_part['content'], data)
        self.assertTrue(data_part['first'])
        self.assertTrue(data_part['last'])
        
        page_part = data_part['page']
        self.assertEqual(page_part['elements'], 4)
        self.assertEqual(page_part['number'], 0)
        self.assertEqual(page_part['offset'], 0)
        self.assertEqual(page_part['size'], 10)
        
        total_part = data_part['total']
        self.assertEqual(total_part['elements'], 4)
        self.assertEqual(total_part['pages'], 1)
        
        sort_part = data_part['sort']
        self.assertTrue(sort_part['default'])
        self.assertEqual(sort_part['field'], 'created_at')
        self.assertEqual(sort_part['direction'], 'desc')

    def test_pagination_with_sort_param(self):
        pagination = StandardResultsSetPagination()
        factory = APIRequestFactory()
        request = factory.get('/?page=1&size=10&sort=name,asc')
        drf_request = Request(request)
        
        # Mocking the page object
        class MockPaginator:
            count = 4
            num_pages = 1

        class MockPage:
            paginator = MockPaginator()
            number = 1
            def has_previous(self): return False
            def has_next(self): return False
            def start_index(self): return 1

        pagination.page = MockPage()
        pagination.request = drf_request
        drf_request.parser_context = {'view': MockView()}
        
        data = [{'id': 1}]
        response = pagination.get_paginated_response(data)
        
        sort_part = response.data['data']['sort']
        self.assertFalse(sort_part['default'])
        self.assertEqual(sort_part['field'], 'name')
        self.assertEqual(sort_part['direction'], 'asc')
