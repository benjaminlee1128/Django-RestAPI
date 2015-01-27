import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    ProviderFactory, InvoiceFactory)


class TestInvoiceEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_post_invoice_without_invoice_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        url = reverse('invoice-list')

        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'number': "",
            'currency': 'RON',
            'invoice_entries': []
        }

        response = self.client.post(url, data=data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            "id": 1,
            "series": "InvoiceSeries",
            "number": 1,
            "provider": "http://testserver/providers/1/",
            "customer": "http://testserver/customers/1/",
            "archived_provider": {},
            "archived_customer": {},
            "due_date": None,
            "issue_date": None,
            "paid_date": None,
            "cancel_date": None,
            "sales_tax_name": "VAT",
            "sales_tax_percent": '1.00',
            "currency": "RON",
            "state": "draft",
            "proforma": None,
            "invoice_entries": []
        }

    def test_post_invoice_with_invoice_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        url = reverse('invoice-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'number': None,
            'currency': 'RON',
            'invoice_entries': [{
                "description": "Page views",
                "unit_price": 10.0,
                "quantity": 20}]
        }

        response = self.client.post(url, data=json.dumps(data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED
        # TODO: Check the body of the response. There were some problems
        # related to the invoice_entries list.


    def test_get_invoices(self):
        batch_size = 50
        InvoiceFactory.create_batch(batch_size)

        url = reverse('invoice-list')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))

    def test_get_invoice(self):
        InvoiceFactory.reset_sequence(1)
        InvoiceFactory.create()

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": 1,
            "series": "InvoiceSeries",
            "number": 1,
            "provider": "http://testserver/providers/1/",
            "customer": "http://testserver/customers/1/",
            "archived_provider": {},
            "archived_customer": {},
            "due_date": None,
            "issue_date": None,
            "paid_date": None,
            "cancel_date": None,
            "sales_tax_name": "VAT",
            "sales_tax_percent": '1.00',
            "currency": "RON",
            "state": "draft",
            "proforma": None,
            "invoice_entries": []
        }

    def test_delete_invoice(self):
        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

