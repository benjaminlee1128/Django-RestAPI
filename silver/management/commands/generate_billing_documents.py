from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import *

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry, Proforma)


class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'

    def _get_proration_percent_and_status(self, subscription, now_date):
        """
        Returns proration percent (how much of the interval will be billed) and
        the status (if the subscription is prorated or not).

        :param date: the date at which the percent and status are computed
        :returns: a tuple containing (Decimal(percent), status) where status
            can be one of [True, False]. The decimal value will be between
            from the interval [0.00; 1.00]
        :rtype: tuple
        """

        # We assume that an invoice/proforma is issued only if
        # plan.interval * plan.interval_count has passed so if we get to this
        # point => an entire billing interval has passed
        if not subscription.is_billed_first_time:
            # An interval has passed and has been billed before
            # => percent = 100%
            return Decimal('1.00'), False
        else:
            # Proration
            now = now_date

            intervals = {
                'year': {'years': -subscription.plan.interval_count},
                'month': {'months': -subscription.plan.interval_count},
                'week': {'weeks': -subscription.plan.interval_count},
                'day': {'days': -subscription.plan.interval_count},
            }

            # This will be UTC, which implies a max difference of 27 hours ~= 1 day
            # NOTE: this will be a negative interval (e.g.: -1 month, -1 week, etc.)
            interval_len = relativedelta(**intervals[subscription.plan.interval])

            # Add the negative value of the interval_len. This will actually
            # be a subtraction which will yield the start of the interval.
            interval_start = now + interval_len
            days_in_interval = (now - interval_start).days
            days_since_subscription_start = (now - self.start_date).days
            percent = 100.0 * days_since_subscription_start / days_in_interval
            percent = Decimal(percent).quantize(Decimal('0.00')) / Decimal('100.0')
            return percent, True

    def _add_plan(self, subscription, now_date, invoice=None,
                  proforma=None):
        interval = '%sly' % subscription.plan.interval

        if not subscription.last_billing_date:
            # First time billing
            start_date = subscription.start_date
            end_date = now_date
        else:
            intervals = {
                'year': {'years': +subscription.plan.interval_count},
                'month': {'months': +subscription.plan.interval_count},
                'week': {'weeks': +subscription.plan.interval_count},
                'day': {'days': +subscription.plan.interval_count},
            }
            interval_len = relativedelta(**intervals[subscription.plan.interval])

            start_date = subscription.last_billing_date
            end_date = subscription.last_billing_date + interval_len

        description = "{plan_name} {interval} plan subscription ({start_date}"\
                      " - {end_date})".format(plan_name=subscription.plan.name,
                                              interval=interval,
                                              start_date=start_date,
                                              end_date=end_date)

        if not subscription.is_on_trial:
            percent, prorated = self._get_proration_percent_and_status(subscription,
                                                                       now_date)
            unit_price = subscription.plan.amount * percent
        else:
            unit_price, prorated = Decimal('0.00'), False

        unit = '%ss' % subscription.plan.interval
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=unit_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

    def _get_units_count(self, included_units, consumed_units):
        if included_units - consumed_units >= 0:
            return 0
        return consumed_units - included_units

    def _add_metered_features(self, subscription, now_date, invoice=None,
                              proforma=None):
        # NOTE: included_units = percent * total_included_units if prorated
        if subscription.last_billing_date:
            start_date = subscription.last_billing_date
        else:
            start_date = subscription.start_date

        for mf in subscription.plan.metered_features.all():
            criteria = {
                'metered_feature': mf,
                'subscription': subscription,
                'start_date__gte': start_date,
            }

            consumed_mf_log = MeteredFeatureUnitsLog.objects.filter(**criteria)
            for log_item in consumed_mf_log:
                percent, prorated = self._get_proration_percent_and_status(subscription,
                                                                           now_date)
                included_units = percent * mf.included_units if prorated else mf.included_units
                total_units = self._get_units_count(included_units,
                                                    log_item.consumed_units)
                unit_price = Decimal('0.00') if subscription.is_on_trial else mf.price_per_unit
                description = "{name} ({start_date} - {end_date})".format(
                    name=mf.name,
                    start_date=log_item.start_date,
                    end_date=log_item.end_date)
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=mf.unit, unit_price=unit_price, quantity=total_units,
                    product_code=mf.product_code
                )

    def _add_plan_entry(self, document, subscription, now_date):
        if subscription.plan.provider_flow == 'proforma':
            plan_entry_args = {'proforma': document}
        else:
            plan_entry_args = {'invoice': document}

        plan_entry_args.update({'subscription': subscription,
                                'now_date': now_date})
        self._add_plan(**plan_entry_args)

    def _add_mf_entries(self, document, subscription, now_date):
        if subscription.plan.provider_flow == 'proforma':
            mf_entry_args = {'proforma': document}
        else:
            mf_entry_args = {'invoice': document}

        mf_entry_args.update({'subscription': subscription,
                              'now_date': now_date})
        self._add_metered_features(**mf_entry_args)

    def _create_document(self, provider, customer, subscription, now_date):
        provider_flow = subscription.plan.provider_flow
        DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

        delta = timedelta(days=customer.payment_due_days)
        due_date = now_date + delta
        document = DocumentModel.objects.create(
            provider=subscription.plan.provider, customer=customer,
            due_date=due_date
        )

        return document

    def _print_status_to_stdout(self, subscription, created=False):
        if subscription.plan.provider_flow == 'proforma':
            doc_name = 'Proforma'
        else:
            doc_name = 'Invoice'
        action = 'Generating' if created else 'Updating'
        msg = '{action} {doc_name} for {subscription}.'.format(
            action=action, doc_name=doc_name, subscription=subscription)

        self.stdout.write(msg)

    def handle(self, *args, **options):
        # Use the same exact date for all the generated documents
        now = timezone.now().date()

        for customer in Customer.objects.all():
            if customer.consolidated_billing:
                # Intermediary document for each provider
                document_per_provider = {}

                # Default doc state (issued, draft) for each provider
                default_doc_state = {}

                # If a subscription is canceld, bill it too => should_be_billed
                # should also check that

                # Process all the active or canceled subscriptions
                subs = customer.subscriptions.filter(state__in=['active', 'canceled'])
                for subscription in subs:
                    if not subscription.should_be_billed:
                        continue

                    provider = subscription.plan.provider

                    default_doc_state[provider] = provider.default_document_state
                    if provider in document_per_provider:
                        document = document_per_provider[provider]
                        self._print_status_to_stdout(subscription,
                                                     created=False)
                    else:
                        document = self._create_document(provider, customer,
                                                         subscription, now)
                        document_per_provider[provider] = document
                        self._print_status_to_stdout(subscription,
                                                     created=True)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(document, subscription, now)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(document, subscription, now)

                    if subscription.state == 'canceled':
                        subscription.end()

                for provider, document in document_per_provider.iteritems():
                    if default_doc_state[provider] == 'issued':
                        document.issue()
                        document.save()
            else:
                # Generate an invoice for each subscription
                for subscription in customer.subscriptions.all():
                    if not subscription.should_be_billed:
                        continue

                    provider = subscription.plan.provider
                    document = self._create_document(provider, customer,
                                                     subscription, now)
                    self._print_status_to_stdout(subscription, created=True)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(document, subscription, now)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(document, subscription, now)

                    if subscription.state == 'canceled':
                        subscription.end()

                    if provider.default_document_state == 'issued':
                        document.issue()
                        document.save()
