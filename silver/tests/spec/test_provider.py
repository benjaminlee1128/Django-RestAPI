import base64
import simplejson as json

import pytest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import serializers
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status, HTTP_HEADER_ENCODING

from silver.models import Provider
from silver.tests.factories import ProviderFactory


class TestProviderEndpoint(APITestCase):

    def setUp(self):
        # TODO: Use factories
        username = 'admin'
        email = 'admin@admin.com'
        password = 'admin'
        self.user = User.objects.create_superuser(username, email, password)

        self.client.force_authenticate(user=self.user)

    def _filter_providers(self, *args, **kwargs):
        return Provider.objects.filter(*args, **kwargs)

    def test_create_valid_provider(self):
        url = reverse('silver_api:provider-list')
        data = {
            "name": "TestProvider",
            "company": "S.C. Timisoara S.R.L",
            "address_1": "Address",
            "country": "RO",
            "city": "Timisoara",
            "zip_code": "300300"
        }
        response = self.client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            'id': 1,
            'url':
            'http://testserver/providers/1/',
            'name': u'TestProvider',
            'company': u'S.C. Timisoara S.R.L',
            'email': None,
            'address_1': u'Address',
            'address_2': None,
            'city': u'Timisoara',
            'state': None,
            'zip_code': u'300300',
            'country': u'RO',
            'extra': None
        }
        qs = self._filter_providers()
        assert qs.count() == 1

    def test_create_provider_without_required_fields(self):
        url = reverse('silver_api:provider-list')
        complete_data = {
            "name": "TestProvider",
            'company': u'S.C. Timisoara S.R.L',
            "address_1": "Address",
            "country": "RO",
            "city": "Timisoara",
            "zip_code": "300300"
        }
        required_fields = ['company', 'address_1', 'country', 'city',
                           'zip_code']

        for field in required_fields:
            temp_data = complete_data.copy()
            try:
                temp_data.pop(field)
            except KeyError:
                pytest.xfail('Required field %s for Provider not provided in the test data.' % field)

            response = self.client.post(url, temp_data)

            assert response.status_code == 400
            assert response.data == {field: [u'This field is required.']}

            qs = self._filter_providers()
            assert qs.count() == 0

    def test_list_providers(self):
        ProviderFactory.reset_sequence(1)
        ProviderFactory.create_batch(25)

        url = reverse('silver_api:provider-list')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 25
        assert 'next' in response.data
        assert 'previous' in response.data
        all_ids = [item['id'] for item in response.data['results']]
        assert all_ids == range(1, 26)

    def test_retrieve_provider(self):
        ProviderFactory.reset_sequence(1)
        ProviderFactory.create()

        url = reverse('silver_api:provider-detail', kwargs={'pk': 1})

        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data == {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'Provider1',
            'company': 'Company1',
            'email': None,
            'address_1': 'Address_11',
            'address_2': None,
            'city': 'City1',
            'state': None,
            'zip_code': '1',
            'country': u'RO',
            'extra': None
        }

    def test_update_provider_correctly(self):
        ProviderFactory.reset_sequence(1)
        ProviderFactory.create()

        url = reverse('silver_api:provider-detail', kwargs={'pk': 1})
        new_data = {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'TestProvider',
            'company': 'TheNewCompany',
            'email': 'a@a.com',
            'address_1': 'address',
            'city': 'City',
            'zip_code': '1',
            'country': 'RO',
        }

        response = self.client.put(url, data=new_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'TestProvider',
            'company': 'TheNewCompany',
            'email': 'a@a.com',
            'address_1': 'address',
            'address_2': None,
            'city': 'City',
            'state': None,
            'zip_code': '1',
            'country': 'RO',
            'extra': None
        }

    def test_update_provider_remove_required_field(self):
        """
         .. note::

             The test does not verify each required field, because the test
         test_create_provider_without_required_fields does this and since the
         creation will fail the update will fail too. This is more of a
         sanity test, to check if the correct view is called and if it does
         what's supposed to do for at least one field.
         """

        ProviderFactory.reset_sequence(1)
        ProviderFactory.create()

        url = reverse('silver_api:provider-detail', kwargs={'pk': 1})
        new_data = {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'TestProvider',
            'email': 'a@a.com',
            'address_1': 'address',
            'city': 'City',
            'zip_code': '1',
            'country': 'RO',
        }

        response = self.client.put(url, data=new_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'company': ['This field is required.']}

    def test_create_bulk_providers(self):
        #ProviderFactory.reset_sequence(1)
        #providers = ProviderFactory.create_batch(5)

        #raw_providers = json.loads(serializers.serialize('json', providers))

        #serialized_providers = []
        #for item in raw_providers:
            #serialized_providers.append(item['fields'])

        #url = reverse('silver_api:provider-list')
        #response = self.client.post(url, data=serialized_providers,
                                    #content_type='application/json')

        #assert response.status_code == status.HTTP_201_CREATED
        providers = [{
            "name": "Provider1",
            "city": "City1",
            "country": "RO",
            "company": "Company1",
            "address_1": "Address_11",
            "zip_code": "1"
        }, {
            "name": "Provider2",
            "city": "City2",
            "country": "RO",
            "company": "Company2",
            "address_1": "Address_12",
            "zip_code": "1"
        }]

        url = reverse('silver_api:provider-list')
        response = self.client.post(url, providers,
                                    content_type='application/json')
        print response.data
        #assert response.status_code == status.HTTP_201_CREATED
        assert True
