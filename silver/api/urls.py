from django.conf.urls import patterns, url

from silver.api import views

urlpatterns = patterns('',
    url(r'^subscriptions/$',
        views.SubscriptionList.as_view(), name='subscription-list'),
    url(r'^subscriptions/(?P<pk>[0-9]+)/$',
        views.SubscriptionDetail.as_view(), name='subscription-detail'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/activate/$',
        views.SubscriptionDetailActivate.as_view(), name='sub-activate'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/cancel/$',
        views.SubscriptionDetailCancel.as_view(), name='sub-cancel'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/reactivate/$',
        views.SubscriptionDetailReactivate.as_view(), name='sub-reactivate'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/(?P<mf>[0-9]+)/$',
        views.MeteredFeatureUnitsLogList.as_view(), name='mf-log-list'),
    url(r'^customers/$',
        views.CustomerList.as_view(), name='customer-list'),
    url(r'^customers/(?P<pk>[0-9]+)/$',
        views.CustomerDetail.as_view(), name='customer-detail'),
    url(r'^plans/$',
        views.PlanList.as_view(), name='plan-list'),
    url(r'^plans/(?P<pk>[0-9]+)/$',
        views.PlanDetail.as_view(), name='plan-detail'),
    url(r'plans/(?P<pk>[0-9]+)/metered-features/$',
        views.PlanMeteredFeatures.as_view(), name='plans-metered-features'),
    url(r'^metered-features/$',
        views.MeteredFeatureList.as_view(), name='metered-feature-list'),
    url(r'^metered-features/(?P<pk>[0-9]+)/$',
        views.MeteredFeatureDetail.as_view(), name='metered-feature-detail'),
    url(r'^providers/$',
        views.ProviderListCreate.as_view(), name='provider-list'),
    url(r'^providers/(?P<pk>[0-9]+)/$',
        views.ProviderRetrieveUpdateDestroy.as_view(), name='provider-detail'),
    url(r'^product-codes/$',
        views.ProductCodeListCreate.as_view(), name='productcode-list'),
    url(r'^product-codes/(?P<pk>[0-9]+)/$',
        views.ProductCodeRetrieveUpdate.as_view(), name='productcode-detail'),
    url(r'^invoices/$',
        views.InvoiceListCreate.as_view(), name='invoice-list'),
    url(r'^invoices/(?P<pk>[0-9]+)/$',
        views.InvoiceRetrieveUpdateDestroy.as_view(), name='invoice-detail'),
    url(r'^invoices/(?P<invoice_pk>[0-9]+)/entries/$',
        views.InvoiceEntryCreate.as_view(), name='billingdocumententry-create'),
    url(r'^invoices/(?P<invoice_pk>[0-9]+)/entries/(?P<entry_id>[0-9]+)/$',
        views.InvoiceEntryUpdateDestroy.as_view(), name=' billingdocumententry-update'),
    url(r'^invoices/(?P<pk>[0-9]+)/state/$',
        views.InvoiceStateHandler.as_view(), name='invoice-state-handler'),
    url(r'^proformas/$',
        views.ProformaListCreate.as_view(), name='proforma-list'),
    url(r'^proformas/(?P<pk>[0-9]+)/$',
        views.ProformaRetrieveUpdateDestroy.as_view(), name='proforma-detail'),
    url(r'^proformas/(?P<proforma_pk>[0-9]+)/entries/$',
        views.ProformaEntryCreate.as_view(), name='proformaentry-create'),
    url(r'^proformas/(?P<proforma_pk>[0-9]+)/entries/(?P<entry_id>[0-9]+)/$',
        views.ProformaEntryUpdateDestroy.as_view(), name='proformaentry-pdate'),
    url(r'^proformas/(?P<pk>[0-9]+)/state/$',
        views.ProformaStateHandler.as_view(), name='proforma-state-handler'),
)
