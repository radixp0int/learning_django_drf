from rest_framework import generics
from rest_framework.test import APIRequestFactory, APITestCase

from core.filtering.mixins import ListDataMixin
from core.pagination.paginator import StandardResultsSetPagination

SAMPLE_DATA = [
    {'id': 1, 'name': 'Widget Pro', 'category': 'hardware', 'price': 99.99},
    {'id': 2, 'name': 'Gadget Basic', 'category': 'hardware', 'price': 29.99},
    {'id': 3, 'name': 'Doohickey Ultra', 'category': 'software', 'price': 149.99},
    {'id': 4, 'name': 'Thingamajig Lite', 'category': 'software', 'price': 49.99},
    {'id': 5, 'name': 'Gizmo Standard', 'category': 'hardware', 'price': 79.99},
]


class SampleListView(ListDataMixin, generics.GenericAPIView):
    pagination_class = StandardResultsSetPagination
    filterable_fields = ['name', 'category']
    sortable_fields = ['name', 'price', 'category']
    default_ordering = ('name', 'asc')

    def get(self, request):
        data = list(SAMPLE_DATA)
        data = self.filter_list(data, request)
        data = self.sort_list(data, request)
        return self.get_paginated_list(data, request)


class ListDataMixinFilterTest(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SampleListView.as_view()

    def _get_content(self, params=''):
        request = self.factory.get(f'/{params}')
        response = self.view(request)
        return response.data['data']['content']

    def test_no_filters_returns_all(self):
        content = self._get_content()
        self.assertEqual(len(content), 5)

    def test_filter_by_name_partial_match(self):
        content = self._get_content('?name=widget')
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['name'], 'Widget Pro')

    def test_filter_by_name_case_insensitive(self):
        content = self._get_content('?name=GADGET')
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['name'], 'Gadget Basic')

    def test_filter_by_category(self):
        content = self._get_content('?category=hardware')
        self.assertEqual(len(content), 3)
        for item in content:
            self.assertEqual(item['category'], 'hardware')

    def test_filter_no_match_returns_empty(self):
        content = self._get_content('?name=nonexistent')
        self.assertEqual(len(content), 0)

    def test_combined_filters(self):
        content = self._get_content('?name=gizmo&category=hardware')
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['name'], 'Gizmo Standard')


class ListDataMixinSortTest(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SampleListView.as_view()

    def _get_content(self, params=''):
        request = self.factory.get(f'/{params}')
        response = self.view(request)
        return response.data['data']['content']

    def test_default_ordering_is_name_asc(self):
        content = self._get_content()
        names = [item['name'] for item in content]
        self.assertEqual(names, sorted(names))

    def test_sort_by_name_asc(self):
        content = self._get_content('?sort=name,asc')
        names = [item['name'] for item in content]
        self.assertEqual(names, sorted(names))

    def test_sort_by_name_desc(self):
        content = self._get_content('?sort=name,desc')
        names = [item['name'] for item in content]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_sort_by_price_asc(self):
        content = self._get_content('?sort=price,asc')
        prices = [item['price'] for item in content]
        self.assertEqual(prices, sorted(prices))

    def test_sort_by_price_desc(self):
        content = self._get_content('?sort=price,desc')
        prices = [item['price'] for item in content]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_invalid_sort_field_ignored(self):
        content = self._get_content('?sort=nonexistent,asc')
        names = [item['name'] for item in content]
        self.assertEqual(names, sorted(names))

    def test_sort_no_direction_defaults_to_asc(self):
        content = self._get_content('?sort=name')
        names = [item['name'] for item in content]
        self.assertEqual(names, sorted(names))


class ListDataMixinPaginationTest(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SampleListView.as_view()

    def test_pagination_envelope_structure(self):
        request = self.factory.get('/?page=1&size=2')
        response = self.view(request)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        data = response.data['data']
        self.assertIn('content', data)
        self.assertIn('page', data)
        self.assertIn('total', data)
        self.assertIn('sort', data)

    def test_page_size_respected(self):
        request = self.factory.get('/?page=1&size=2')
        response = self.view(request)
        self.assertEqual(len(response.data['data']['content']), 2)

    def test_total_elements(self):
        request = self.factory.get('/?page=1&size=2')
        response = self.view(request)
        self.assertEqual(response.data['data']['total']['elements'], 5)

    def test_first_page_flag(self):
        request = self.factory.get('/?page=1&size=2')
        response = self.view(request)
        self.assertTrue(response.data['data']['first'])
        self.assertFalse(response.data['data']['last'])

    def test_last_page_flag(self):
        request = self.factory.get('/?page=3&size=2')
        response = self.view(request)
        self.assertTrue(response.data['data']['last'])

    def test_filter_then_paginate(self):
        request = self.factory.get('/?category=hardware&page=1&size=2')
        response = self.view(request)
        self.assertEqual(len(response.data['data']['content']), 2)
        self.assertEqual(response.data['data']['total']['elements'], 3)


class ListDataMixinSortReportingTest(APITestCase):
    """
    ListDataMixin views declare default_ordering, not `ordering`, so the
    paginator can't read their default off the view — the mixin publishes it.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SampleListView.as_view()

    def _sort_block(self, params=''):
        return self.view(self.factory.get(f'/{params}')).data['data']['sort']

    def test_unsorted_reports_default_ordering_not_created_at(self):
        sort = self._sort_block()
        # SampleListView has no created_at field at all — reporting one would be a lie.
        self.assertTrue(sort['default'])
        self.assertEqual(sort['field'], 'name')
        self.assertEqual(sort['direction'], 'asc')

    def test_explicit_sort_is_reported(self):
        sort = self._sort_block('?sort=price,desc')
        self.assertFalse(sort['default'])
        self.assertEqual(sort['field'], 'price')
        self.assertEqual(sort['direction'], 'desc')
        self.assertEqual(sort['fields'], [{'field': 'price', 'direction': 'desc'}])

    def test_invalid_sort_field_reports_the_default_actually_used(self):
        sort = self._sort_block('?sort=nonexistent,desc')
        self.assertTrue(sort['default'])
        self.assertEqual(sort['field'], 'name')
        self.assertEqual(sort['direction'], 'asc')

    def test_sort_without_direction_reports_asc(self):
        sort = self._sort_block('?sort=price')
        self.assertFalse(sort['default'])
        self.assertEqual(sort['direction'], 'asc')
