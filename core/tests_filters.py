from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import generics
from miniapp.models import Item, Tenant, Feedback
from miniapp.views import ItemFilter, FeedbackFilter, ItemViewSet, FeedbackViewSet
from core.filters import CustomOrderingFilter
from rest_framework.serializers import ModelSerializer

class ItemSerializer(ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

class ItemListView(generics.ListAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    filter_backends = [CustomOrderingFilter]
    ordering_fields = ['name', 'created_at']
    ordering = ['name']  # default ordering
    pagination_class = None  # disable global pagination for ordering-only tests

class CustomOrderingFilterTest(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        Item.objects.create(name='B Item', description='Desc B')
        Item.objects.create(name='A Item', description='Desc A')
        Item.objects.create(name='C Item', description='Desc C')

    def test_default_ordering(self):
        request = self.factory.get('/')
        view = ItemListView.as_view()
        response = view(request)
        names = [item['name'] for item in response.data]
        self.assertEqual(names, ['A Item', 'B Item', 'C Item'])

    def test_sort_asc(self):
        request = self.factory.get('/', {'sort': 'name,asc'})
        view = ItemListView.as_view()
        response = view(request)
        names = [item['name'] for item in response.data]
        self.assertEqual(names, ['A Item', 'B Item', 'C Item'])

    def test_sort_desc(self):
        request = self.factory.get('/', {'sort': 'name,desc'})
        view = ItemListView.as_view()
        response = view(request)
        names = [item['name'] for item in response.data]
        self.assertEqual(names, ['C Item', 'B Item', 'A Item'])

    def test_sort_no_direction_defaults_to_asc(self):
        request = self.factory.get('/', {'sort': 'name'})
        view = ItemListView.as_view()
        response = view(request)
        names = [item['name'] for item in response.data]
        self.assertEqual(names, ['A Item', 'B Item', 'C Item'])

    def test_invalid_sort_field_ignored(self):
        request = self.factory.get('/', {'sort': 'nonexistent_field,asc'})
        view = ItemListView.as_view()
        response = view(request)
        # Falls back to default ordering when invalid field is given
        names = [item['name'] for item in response.data]
        self.assertEqual(names, ['A Item', 'B Item', 'C Item'])


class ItemFilterTest(APITestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Acme Corp')
        self.tenant_b = Tenant.objects.create(name='Beta LLC')

        self.item1 = Item.objects.create(name='Widget', description='A small widget')
        self.item2 = Item.objects.create(name='Gadget', description='A useful gadget')
        self.item3 = Item.objects.create(name='Doohickey', description='Mysterious device')

        Feedback.objects.create(item=self.item1, tenant=self.tenant_a, content='Great product', rating=5)
        Feedback.objects.create(item=self.item2, tenant=self.tenant_b, content='Decent quality', rating=3)
        Feedback.objects.create(item=self.item3, tenant=self.tenant_a, content='Terrible experience', rating=1)

    def test_filter_by_name(self):
        f = ItemFilter({'name': 'wid'}, queryset=Item.objects.all())
        self.assertEqual(list(f.qs), [self.item1])

    def test_filter_by_name_case_insensitive(self):
        f = ItemFilter({'name': 'WIDGET'}, queryset=Item.objects.all())
        self.assertEqual(list(f.qs), [self.item1])

    def test_filter_by_feedback_content(self):
        f = ItemFilter({'feedback_content': 'great'}, queryset=Item.objects.all())
        self.assertEqual(list(f.qs), [self.item1])

    def test_filter_by_feedback_rating(self):
        f = ItemFilter({'feedback_rating': 3}, queryset=Item.objects.all())
        self.assertEqual(list(f.qs), [self.item2])

    def test_filter_by_feedback_tenant_name(self):
        f = ItemFilter({'feedback_tenant_name': 'acme'}, queryset=Item.objects.all())
        results = list(f.qs)
        self.assertIn(self.item1, results)
        self.assertIn(self.item3, results)
        self.assertNotIn(self.item2, results)

    def test_filter_by_feedback_tenant_name_case_insensitive(self):
        f = ItemFilter({'feedback_tenant_name': 'ACME'}, queryset=Item.objects.all())
        self.assertEqual(f.qs.count(), 2)


class FeedbackFilterTest(APITestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Acme Corp')
        self.tenant_b = Tenant.objects.create(name='Beta LLC')

        self.item1 = Item.objects.create(name='Widget', description='A small widget')
        self.item2 = Item.objects.create(name='Gadget', description='A useful gadget')

        self.fb1 = Feedback.objects.create(item=self.item1, tenant=self.tenant_a, content='Great product', rating=5)
        self.fb2 = Feedback.objects.create(item=self.item2, tenant=self.tenant_b, content='Decent quality', rating=3)
        self.fb3 = Feedback.objects.create(item=self.item1, tenant=self.tenant_b, content='Average at best', rating=2)

    def test_filter_by_content(self):
        f = FeedbackFilter({'content': 'great'}, queryset=Feedback.objects.all())
        self.assertEqual(list(f.qs), [self.fb1])

    def test_filter_by_rating(self):
        f = FeedbackFilter({'rating': 3}, queryset=Feedback.objects.all())
        self.assertEqual(list(f.qs), [self.fb2])

    def test_filter_by_item_name(self):
        f = FeedbackFilter({'item_name': 'widget'}, queryset=Feedback.objects.all())
        results = list(f.qs)
        self.assertIn(self.fb1, results)
        self.assertIn(self.fb3, results)
        self.assertNotIn(self.fb2, results)

    def test_filter_by_tenant_name(self):
        f = FeedbackFilter({'tenant_name': 'beta'}, queryset=Feedback.objects.all())
        results = list(f.qs)
        self.assertIn(self.fb2, results)
        self.assertIn(self.fb3, results)
        self.assertNotIn(self.fb1, results)

    def test_filter_by_tenant_name_case_insensitive(self):
        f = FeedbackFilter({'tenant_name': 'BETA'}, queryset=Feedback.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_combined_filters(self):
        f = FeedbackFilter({'item_name': 'widget', 'tenant_name': 'beta'}, queryset=Feedback.objects.all())
        self.assertEqual(list(f.qs), [self.fb3])
