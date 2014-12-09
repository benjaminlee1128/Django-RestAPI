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
        views.MeteredFeaturesList.as_view(), name='metered-feature-list'),
    url(r'^metered-features/(?P<pk>[0-9]+)/$',
        views.MeteredFeaturesDetail.as_view(), name='metered-feature-detail'),
    url(r'^providers/$',
        views.ProviderListBulkCreate.as_view(), name='provider-list'),
    url(r'^providers/(?P<pk>[0-9]+)/$',
        views.ProviderRetrieveUpdateDestroy.as_view(), name='provider-detail'),
    url(r'^invoices/$',
        views.InvoiceListBulkCreate.as_view(), name='invoice-list'),
    url(r'^invoices/(?P<pk>[0-9]+)/$',
        views.InvoiceRetrieveUpdateDestroy.as_view(), name='invoice-detail'),
)

def f():
    pass
