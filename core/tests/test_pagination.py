from rest_framework import generics
from rest_framework.request import Request
from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIRequestFactory, APITestCase

from core.filtering.backends import CustomOrderingFilter
from core.pagination.paginator import StandardResultsSetPagination
from miniapp.models import Item


class MockView:
    ordering = ['-created_at']


class ItemSerializer(ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'


class OrderedItemListView(generics.ListAPIView):
    """Real view wired to CustomOrderingFilter — MockView above bypasses it."""

    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    filter_backends = [CustomOrderingFilter]
    pagination_class = StandardResultsSetPagination
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']


class PaginationTest(APITestCase):
    def test_standard_results_set_pagination_structure(self):
        pagination = StandardResultsSetPagination()
        factory = APIRequestFactory()
        request = factory.get('/?page=1&size=10')
        drf_request = Request(request)

        class MockPaginator:
            count = 4
            num_pages = 1

        class MockPage:
            paginator = MockPaginator()
            number = 1

            def has_previous(self):
                return False

            def has_next(self):
                return False

            def start_index(self):
                return 1

        pagination.page = MockPage()
        pagination.request = drf_request
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
        self.assertEqual(page_part['offset'], 1)
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

        class MockPaginator:
            count = 4
            num_pages = 1

        class MockPage:
            paginator = MockPaginator()
            number = 1

            def has_previous(self):
                return False

            def has_next(self):
                return False

            def start_index(self):
                return 1

        pagination.page = MockPage()
        pagination.request = drf_request
        drf_request.parser_context = {'view': MockView()}

        data = [{'id': 1}]
        response = pagination.get_paginated_response(data)

        sort_part = response.data['data']['sort']
        self.assertFalse(sort_part['default'])
        self.assertEqual(sort_part['field'], 'name')
        self.assertEqual(sort_part['direction'], 'asc')


class AppliedSortReportingTest(APITestCase):
    """
    The envelope's 'sort' block must report the ordering that was actually
    applied, not echo back whatever the client asked for.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = OrderedItemListView.as_view()
        Item.objects.create(name='B Item', description='Desc B')
        Item.objects.create(name='A Item', description='Desc A')

    def _sort_block(self, params=''):
        return self.view(self.factory.get(f'/{params}')).data['data']['sort']

    def test_valid_sort_is_reported(self):
        sort = self._sort_block('?sort=name,asc')
        self.assertFalse(sort['default'])
        self.assertEqual(sort['field'], 'name')
        self.assertEqual(sort['direction'], 'asc')

    def test_invalid_sort_field_reports_the_default_actually_used(self):
        sort = self._sort_block('?sort=bogus_field,asc')
        # Rows fall back to the view default, so the envelope must say so
        # rather than echoing 'bogus_field'.
        self.assertTrue(sort['default'])
        self.assertEqual(sort['field'], 'created_at')
        self.assertEqual(sort['direction'], 'desc')

    def test_no_sort_param_reports_view_default(self):
        sort = self._sort_block()
        self.assertTrue(sort['default'])
        self.assertEqual(sort['field'], 'created_at')
        self.assertEqual(sort['direction'], 'desc')

    def test_multi_field_sort_lists_every_applied_term(self):
        sort = self._sort_block('?sort=name,asc,created_at,desc')
        self.assertEqual(
            sort['fields'],
            [
                {'field': 'name', 'direction': 'asc'},
                {'field': 'created_at', 'direction': 'desc'},
            ],
        )
        # Primary term stays mirrored on field/direction for compatibility.
        self.assertEqual(sort['field'], 'name')
        self.assertEqual(sort['direction'], 'asc')

    def test_single_sort_still_populates_fields(self):
        sort = self._sort_block('?sort=name,desc')
        self.assertEqual(sort['fields'], [{'field': 'name', 'direction': 'desc'}])

    def test_partially_invalid_multi_sort_keeps_only_valid_terms(self):
        sort = self._sort_block('?sort=name,asc,bogus_field,desc')
        self.assertEqual(sort['fields'], [{'field': 'name', 'direction': 'asc'}])
        self.assertFalse(sort['default'])
