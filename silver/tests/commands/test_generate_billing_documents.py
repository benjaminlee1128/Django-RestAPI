import datetime as dt
from decimal import Decimal, ROUND_UP, ROUND_HALF_UP, Context

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from django.utils import timezone
from mock import patch, PropertyMock, MagicMock

from silver.models import (Proforma, DocumentEntry, Invoice, Subscription,
                           Customer, MeteredFeatureUnitsLog, BillingLog)
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory,
                                    MeteredFeatureUnitsLogFactory,
                                    CustomerFactory, ProviderFactory)
from silver.utils import get_object_or_None


class TestInvoiceGenerationCommand(TestCase):
    """
    Tests:
        * non-canceled
            * consolidated billing w/ included units --
            * consolidated billing w/a included units --
            * prorated subscriptions w/ consumed mfs underflow --
            * prorated subscriptions w/ consumed mfs overflow --
            * consolidated -> subscriptions full as well as full trial
            * non-consolidated billing w/ included units --
            * non-consolidated billing w/a included units --
            * non-consolidated billing w/ prorated subscriptions
            * Generate with different default states
                * draft --
                * issued --
            * trial over multiple months --
            * variations for non-canceled subscriptions. Check the cases paper
        * canceled
            * canceled subscription w/ trial --
            * canceled subscription w/a trial
            * canceled subscription w trial underflow --
            * canceled subscription w trial overflow --
        * sales tax percent
        * generate_after

        TODO: add missing test descriptions
    """

    def __init__(self, *args, **kwargs):
        super(TestInvoiceGenerationCommand, self).__init__(*args, **kwargs)
        self.output = StringIO()

    ###########################################################################
    # Non-Canceled
    ###########################################################################
    def test_gen_for_non_consolidated_billing_with_consumed_units(self):
        """
        A customer  has 3 subscriptions for which we use the normal case:
            * add consumed mfs for the previous month
            * add the value of the plan for the next month
            => 3 different proformas
        """
        billing_date = '2015-03-01'

        customer = CustomerFactory.create(consolidated_billing=False)
        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

        # Create 3 subscriptions for the same customer
        SubscriptionFactory.create_batch(size=3,
                                         plan=plan, start_date=start_date,
                                         customer=customer)

        consumed_mfs = Decimal('50.00')
        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()

            # For each subscription, add consumed units
            MeteredFeatureUnitsLogFactory.create(
                subscription=subscription,
                metered_feature=metered_feature,
                start_date=dt.date(2015, 2, 1),
                end_date=dt.date(2015, 2, 28),
                consumed_units=consumed_mfs)

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 3
            assert Invoice.objects.all().count() == 0

            assert DocumentEntry.objects.all().count() == 6

            for proforma in Proforma.objects.all():
                entries = proforma.proforma_entries.all()
                if 'plan' in entries[0].description.lower():
                    plan = entries[0]
                    units = entries[1]
                else:
                    units = entries[0]
                    plan = entries[1]

                assert plan.quantity == 1
                assert plan.unit_price == plan_price
                assert units.quantity == consumed_mfs
                assert units.unit_price == metered_feature.price_per_unit

    def test_gen_for_non_consolidated_billing_without_consumed_units(self):
        """
        A customer  has 3 subscriptions for which he does not have any
        consumed units => 3 different proformas, each containing only the
        plan's value.
        """
        billing_date = '2015-03-01'

        customer = CustomerFactory.create(consolidated_billing=False)
        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

        # Create 3 subscriptions for the same customer
        SubscriptionFactory.create_batch(size=3,
                                         plan=plan, start_date=start_date,
                                         customer=customer)

        consumed_mfs = Decimal('50.00')
        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 3
            assert Invoice.objects.all().count() == 0

            for proforma in Proforma.objects.all():
                entries = proforma.proforma_entries.all()
                assert entries.count() == 1
                assert entries[0].quantity == 1
                assert entries[0].unit_price == plan_price


    def test_gen_consolidated_billing_with_consumed_mfs(self):
        """
        A customer  has 3 subscriptions for which we use the normal case:
            * add consumed mfs for the previous month for each subscription
            * add the value of the plan for the next month for each subscription
            => 1 proforma with all the aforementioned data
        """

        billing_date = '2015-03-01'
        subscriptions_cnt = 3

        customer = CustomerFactory.create(
            consolidated_billing=True,
            sales_tax_percent=Decimal('0.00'))
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'), price_per_unit=mf_price)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

        subscriptions = SubscriptionFactory.create_batch(
            size=subscriptions_cnt, plan=plan, start_date=start_date,
            customer=customer)

        consumed_mfs = Decimal('50.00')
        for subscription in subscriptions:
            subscription.activate()
            subscription.save()

            # For each subscription, add consumed units
            MeteredFeatureUnitsLogFactory.create(
                subscription=subscription,
                metered_feature=metered_feature,
                start_date=dt.date(2015, 2, 1),
                end_date=dt.date(2015, 2, 28),
                consumed_units=consumed_mfs)

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            proforma = Proforma.objects.get(id=1)
            # For each doc, expect 2 entries: the plan value and the mfs
            assert proforma.proforma_entries.all().count() == subscriptions_cnt * 2

            expected_total = (subscriptions_cnt * plan_price +
                              subscriptions_cnt * (mf_price * consumed_mfs))
            assert proforma.total == expected_total

    def test_gen_consolidated_billing_without_mfs(self):
        """
        A customer has 3 subscriptions for which it does not have any
        consumed metered features.
        """

        billing_date = '2015-03-01'
        subscriptions_cnt = 3

        customer = CustomerFactory.create(
            consolidated_billing=True,
            sales_tax_percent=Decimal('0.00'))
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'), price_per_unit=mf_price)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

        subscriptions = SubscriptionFactory.create_batch(
            size=subscriptions_cnt, plan=plan, start_date=start_date,
            customer=customer)

        for subscription in subscriptions:
            subscription.activate()
            subscription.save()

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            proforma = Proforma.objects.get(id=1)
            # For each doc, expect 1 entry: the plan value
            assert proforma.proforma_entries.all().count() == subscriptions_cnt

            expected_total = subscriptions_cnt * plan_price
            assert proforma.total == expected_total

    def ttest_prorated_subscription_with_consumed_mfs_underflowest_prorated_subscription_with_consumed_mfs_underflow(self):
        """
        The subscription started last month and it does not have a trial
        => prorated value for the plan; the consumed_mfs < included_mfs
        => 1 proforma with 1 single value, corresponding to the plan for the
        next month
        """

        prev_billing_date = '2015-02-14'
        curr_billing_date = '2015-03-02'

        customer = CustomerFactory.create(
            consolidated_billing=False, sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(included_units=Decimal('20.00'))
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer, trial_end=None)
        subscription.activate()
        subscription.save()

        call_command('generate_docs', date=prev_billing_date,
                    stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 14), end_date=dt.date(2015, 2, 28),
            consumed_units=Decimal('10.00'))

        call_command('generate_docs', date=curr_billing_date,
                    stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=2)
        # Expect 1 entry: the plan for the next month.
        # The mfs will not be added as the consumed_mfs < included_mfs
        assert proforma.proforma_entries.all().count() == 1
        assert proforma.total == plan_price

    def test_prorated_subscription_with_consumed_mfs_overflow(self):
        prev_billing_date = '2015-02-15'
        curr_billing_date = '2015-03-02'

        customer = CustomerFactory.create(consolidated_billing=False,
                                          sales_tax_percent=Decimal('0.00'))

        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(included_units=Decimal('20.00'),
                                                price_per_unit=mf_price)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 15)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        call_command('generate_docs', date=prev_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=1)
        assert proforma.total == Decimal(14/28.0) * plan_price
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])

        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 15), end_date=dt.date(2015, 2, 28),
            consumed_units=Decimal('12.00'))

        call_command('generate_docs', date=curr_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=2)
        # Expect 2 entries: the plan for the next month + the extra consumed
        # units. extra_mfs = 2, since included_mfs=20 but the plan is
        # 50% prorated => only 50% of the total included_mfs are included.
        # The mfs will not be added as the consumed_mfs < included_mfs
        assert proforma.proforma_entries.all().count() == 2
        assert proforma.total == plan_price + mf_price * 2
        # mfs for last month
        assert proforma.proforma_entries.all()[0].prorated == True
        # plan for upcoming month
        assert proforma.proforma_entries.all()[1].prorated == False

    def test_subscription_with_trial_without_metered_features_to_draft(self):
        billing_date = '2015-03-02'

        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=15, amount=plan_price)

        start_date = dt.date(2015, 2, 4)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days - 1)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        Customer.objects.get(id=1).sales_tax_percent = Decimal('0.00')

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 4 entries:
            # Plan Trial (+-), Plan Prorated (+), Plan for next month(+)
            assert DocumentEntry.objects.all().count() == 4

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('107.1400')  # (15 / 28) * 200

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-107.1400')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == Decimal('71.4200') # (10 / 28) * 200

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == plan_price

            # And quantity 1
            assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_underflow_to_draft(self):
        billing_date = '2015-03-01'

        included_units_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=included_units_during_trial)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date)
        subscription.activate()
        subscription.save()

        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)
        consumed_mfs_during_trial = Decimal('3.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=consumed_mfs_during_trial)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 7 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-), Plan After Trial (+)
            # Metered Features After Trial (+), Plan for next month (+)
            assert DocumentEntry.objects.all().count() == 7

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == consumed_mfs_during_trial

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == consumed_mfs_during_trial

            doc = get_object_or_None(DocumentEntry, id=5)
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=7)
            assert doc.unit_price == plan_price

            # And quantity 1
            assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_overflow_to_draft(self):
        billing_date = '2015-03-01'

        units_included_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=units_included_during_trial)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        units_consumed_during_trial = Decimal('7.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=units_consumed_during_trial
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 7 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Extra units consumed during trial (+)
            # Plan After Trial (+)
            # Metered Features After Trial (+), Plan for next month (+)
            assert DocumentEntry.objects.all().count() == 8

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=5)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_consumed_during_trial - units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=6)
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=7)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=8)
            assert doc.unit_price == Decimal('200.00')

            # And quantity 1
            assert doc.quantity == 1

    def test_on_trial_with_consumed_units_underflow(self):
        billing_date = '2015-03-02'

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=Decimal('10.00'))
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 20), end_date=dt.date(2015, 2, 28),
            consumed_units=Decimal('8.00'))

        mocked_is_billed_first_time = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            proforma = Proforma.objects.get(id=1)
            # Expect 4 entries:
            # - prorated subscription
            # - prorated subscription discount
            # - consumed mfs
            # - consumed mfs discount
            assert proforma.proforma_entries.count() == 4
            assert all([entry.prorated
                        for entry in proforma.proforma_entries.all()])
            assert all([entry.total != Decimal('0.0000')
                        for entry in proforma.proforma_entries.all()])
            assert proforma.total == Decimal('0.0000')

    def test_on_trial_with_consumed_units_overflow(self):
        billing_date = '2015-03-02'

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        mf_price = Decimal('2.5')
        included_during_trial = Decimal('10.00')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial,
            price_per_unit=mf_price)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_trial = Decimal('12.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 20), end_date=dt.date(2015, 2, 28),
            consumed_units=consumed_during_trial)

        mocked_is_billed_first_time = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            proforma = Proforma.objects.get(id=1)
            # Expect 4 entries:
            # - prorated subscription
            # - prorated subscription discount
            # - consumed mfs
            # - consumed mfs discount
            # - extra consumed mfs
            assert proforma.proforma_entries.count() == 5
            assert all([entry.prorated
                        for entry in proforma.proforma_entries.all()])
            assert all([entry.total != Decimal('0.0000')
                        for entry in proforma.proforma_entries.all()])
            extra_during_trial = consumed_during_trial - included_during_trial
            assert proforma.total == extra_during_trial * mf_price

    def test_2nd_sub_after_trial_with_consumed_units_underflow(self):
        """
        The subscription:
            * start_date=2015-05-20
            * trial_end=2015-06-03
            * first billing_date=2015-06-01
            * second billing_date=2015-06-04 (right after the trial_end)
        The consumed_during_trial < included_during_trial
        """

        ## SETUP ##
        prev_billing_date = '2015-06-01'
        curr_billing_date = '2015-06-04' # First day after trial_end

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        included_during_trial = Decimal('10.00')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_first_trial_part = Decimal('5.00')
        consumed_during_second_trial_part = Decimal('5.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 5, 20), end_date=dt.date(2015, 5, 31),
            consumed_units=consumed_during_first_trial_part)
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 3),
            consumed_units=consumed_during_second_trial_part)

        ## TEST ##
        call_command('generate_docs', billing_date=prev_billing_date,
                        stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        assert Proforma.objects.get(id=1).total == Decimal('0.0000')

        call_command('generate_docs', billing_date=curr_billing_date,
                        stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=2)
        # Expect 5 entries:
        # - prorated subscription
        # - prorated subscription discount
        # - consumed mfs from trial
        # - consumed mfs from trial discount
        # - prorated subscription for the remaining period
        assert proforma.proforma_entries.count() == 5
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        prorated_plan_value = (Decimal(27/30.0) * plan_price).quantize(Decimal('0.000'))
        assert proforma.total == prorated_plan_value

    def test_2nd_sub_billing_after_trial_with_all_consumed_units_overflow(self):
        """
        The subscription:
            * start_date=2015-05-20
            * trial_end=2015-06-03
            * first billing_date=2015-06-01
            * second billing_date=2015-06-04 (right after the trial_end)
        During 2014-05-20->2015-06-03 all the included_during_trial units have
        been consumed.
        """

        ## SETUP ##
        prev_billing_date = '2015-06-01'
        curr_billing_date = '2015-06-04' # First day after trial_end

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        included_during_trial = Decimal('10.00')
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial,
            price_per_unit=mf_price)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_first_trial_part = Decimal('10.00')
        consumed_during_second_trial_part = Decimal('12.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 5, 20), end_date=dt.date(2015, 5, 31),
            consumed_units=consumed_during_first_trial_part)
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 3),
            consumed_units=consumed_during_second_trial_part)

        ## TEST ##
        call_command('generate_docs', billing_date=prev_billing_date,
                        stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        assert Proforma.objects.get(id=1).total == Decimal('0.0000')

        call_command('generate_docs', billing_date=curr_billing_date,
                        stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=2)
        # Expect 4 entries:
        # - prorated subscription
        # - prorated subscription discount
        # - consumed mfs from trial
        # - prorated subscription for the remaining period
        assert proforma.proforma_entries.count() == 4
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        prorated_plan_value = (Decimal(27/30.0) * plan_price).quantize(Decimal('0.000'))
        extra_mfs_during_trial = consumed_during_second_trial_part * mf_price
        assert proforma.total == prorated_plan_value + extra_mfs_during_trial

    def test_2nd_sub_billing_after_trial_with_some_consumed_units_overflow(self):
        """
        The subscription:
            * start_date=2015-05-20
            * trial_end=2015-06-03
            * first billing_date=2015-06-01
            * second billing_date=2015-06-04 (right after the trial_end)
        During 2015-05-20->2015-06-03 only a part of the included units have
        been consumed => a part remain for the 2015-06-01->2015-06-03
        """

        ## SETUP ##
        prev_billing_date = '2015-06-01'
        curr_billing_date = '2015-06-04' # First day after trial_end

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        included_during_trial = Decimal('12.00')
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial,
            price_per_unit=mf_price)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_first_trial_part = Decimal('10.00')
        consumed_during_second_trial_part = Decimal('12.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 5, 20), end_date=dt.date(2015, 5, 31),
            consumed_units=consumed_during_first_trial_part)
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 3),
            consumed_units=consumed_during_second_trial_part)

        ## TEST ##
        call_command('generate_docs', billing_date=prev_billing_date,
                        stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        assert Proforma.objects.get(id=1).total == Decimal('0.0000')

        call_command('generate_docs', billing_date=curr_billing_date,
                        stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=2)
        # Expect 6 entries:
        # - prorated subscription
        # - prorated subscription discount
        # - prorated consumed units during trial
        # - prorated consumed units during trial discount
        # - extra consumed mfs from trial
        # - prorated subscription for the remaining period
        assert proforma.proforma_entries.count() == 6
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        prorated_plan_value = (Decimal(27/30.0) * plan_price).quantize(Decimal('0.000'))
        extra_mfs_during_trial = 10 * mf_price
        assert proforma.total == prorated_plan_value + extra_mfs_during_trial

    def test_2nd_sub_after_prorated_month_without_trial_without_consumed_units(self):
        """
        The subscription:
            * start_date=2015-05-20, no trial
            * first billing_date=2015-05-20 (right after activating
            the subscription)
            * second billing_date=2015-06-01 (right after the trial_end)
        It has 0 consumed units during 2015-05-20 -> 2015-06-01.
        """

        ## SETUP ##
        prev_billing_date = '2015-05-20'
        curr_billing_date = '2015-06-01'

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        metered_feature = MeteredFeatureFactory()
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer, trial_end=None)
        subscription.activate()
        subscription.save()

        ## TEST ##
        call_command('generate_docs', date=prev_billing_date,
                     subscription=subscription.id, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        percent = Decimal(12/31.0).quantize(Decimal('0.0000'))
        assert Proforma.objects.get(id=1).total == percent * plan_price

        call_command('generate_docs', date=curr_billing_date,
                     subscription=subscription.id, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.get(id=2)
        # Expect 1 entries: the subscription for the next month
        assert proforma.proforma_entries.count() == 1
        assert all([not entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert proforma.total == plan_price

    def test_prorated_month_without_trial_with_consumed_units(self):
        assert True

    def test_full_month_with_consumed_units(self):
        assert True

    def test_full_month_without_consumed_units(self):
        assert True

    def test_gen_proforma_to_issued_state_for_one_provider(self):
        billing_date = '2015-03-02'

        customer = CustomerFactory.create(
            consolidated_billing=False, sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(included_units=Decimal('20.00'))
        provider = ProviderFactory.create(default_document_state='issued')
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, provider=provider,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        mocked_should_be_billed = MagicMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            should_be_billed=mocked_should_be_billed):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            assert Proforma.objects.get(id=1).state == 'issued'

    def test_gen_mixed_states_for_multiple_providers(self):
        billing_date = '2015-03-02'

        customer = CustomerFactory.create(
            consolidated_billing=False, sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('20.00'))
        provider_draft = ProviderFactory.create(
            default_document_state='draft')
        provider_issued = ProviderFactory.create(
            default_document_state='issued')
        plan_price = Decimal('200.00')
        plan1 = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, provider=provider_draft,
                                  metered_features=[metered_feature])
        plan2 = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price, provider=provider_issued,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        # Create the prorated subscription
        subscription1 = SubscriptionFactory.create(
            plan=plan1, start_date=start_date, customer=customer)
        subscription1.activate()
        subscription1.save()

        subscription2 = SubscriptionFactory.create(
            plan=plan2, start_date=start_date, customer=customer)
        subscription2.activate()
        subscription2.save()

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 14))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        mocked_get_consumed_units_during_trial= MagicMock(return_value=(0, 0))
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time,
                            _get_extra_consumed_units_during_trial=\
                            mocked_get_consumed_units_during_trial):

            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 2
            assert Invoice.objects.all().count() == 0

            assert Proforma.objects.get(id=1).state == 'draft'
            assert Proforma.objects.get(id=2).state == 'issued'

    ###########################################################################
    # Canceled
    ###########################################################################
    def test_canceled_subscription_with_trial_and_consumed_metered_features_draft(self):
        """
        Subscription with consumed mfs both during trial and afterwards,
        canceled in the same month it started.

        start_date = 2015-02-01
        trial_end  = 2015-02-08 -- has consumed units during trial period
        end_date   = 2015-02-24 -- has consumed units between trial and end_date
        """

        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 02, 01)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 6 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Plan After Trial (+),  Metered Features After Trial (+)
            assert DocumentEntry.objects.all().count() == 6

            doc = get_object_or_None(DocumentEntry, id=1) # Plan trial (+)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2) # Plan trial (-)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3) # Consumed mf (+)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_during_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=4) # Consumed mf (-)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_during_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=5) # Plan after trial end
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6) # Consumed mf after trial
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_canceled_subscription_with_metered_features_to_draft(self):
        """
        start_date        = 2015-01-01
        trial_end         = 2015-01-08
        last_billing_date = 2015-02-01
        """
        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 1)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        mf_units_log = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.datetime(2015, 2, 1),
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = PropertyMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1)
        )
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # Expect 1 entry:
            # Extra Metered Features (+)
            assert DocumentEntry.objects.all().count() == 1

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log.consumed_units

    def test_canceled_subscription_with_trial_and_trial_underflow(self):
        """
        A subscription that was canceled in the same month as it started,
        the customer consuming less metered features than
        included_units_during_trial.
        """

        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=Decimal('5.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 02, 01)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        trial_quantity = Decimal('3.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=trial_quantity)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 6 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Plan After Trial (+),  Metered Features After Trial (+)
            assert DocumentEntry.objects.all().count() == 6

            doc = get_object_or_None(DocumentEntry, id=1) # Plan trial (+)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2) # Plan trial (-)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3) # Consumed mf (+)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == trial_quantity

            doc = get_object_or_None(DocumentEntry, id=4) # Consumed mf (-)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == trial_quantity

            doc = get_object_or_None(DocumentEntry, id=5) # Plan after trial end
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6) # Consumed mf after trial
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_canceled_subscription_with_trial_and_trial_overflow(self):
        billing_date = '2015-03-01'

        units_included_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=units_included_during_trial)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 02, 01)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        units_consumed_during_trial = Decimal('7.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=units_consumed_during_trial)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 7 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Extra consumed mf
            # Plan After Trial (+),  Metered Features After Trial (+)
            assert DocumentEntry.objects.all().count() == 7

            doc = get_object_or_None(DocumentEntry, id=1) # Plan trial (+)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2) # Plan trial (-)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3) # Consumed mf (+)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=4) # Consumed mf (-)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=5) # Consumed mf (-)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_consumed_during_trial - units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=6) # Plan after trial end
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=7) # Consumed mf after trial
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_gen_for_single_canceled_subscription(self):
        billing_date = '2015-04-03'

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = dt.date(2014, 1, 3)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        mocked_on_trial = MagicMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', subscription='1',
                         billing_date=billing_date, stdout=self.output)

            assert Subscription.objects.filter(state='ended').count() == 1

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # TODO: test what's added on the proforma

    def test_gen_active_and_canceled_selection(self):
        billing_date = '2015-02-09'

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = dt.date(2015, 1, 29)

        SubscriptionFactory.create_batch(
            size=5, plan=plan, start_date=start_date)
        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()
        for subscription in Subscription.objects.filter(id__gte=2, id__lte=4):
            subscription.cancel()
            subscription.save()

        mocked_on_trial = MagicMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect 5 Proformas (2 active Subs, 3 canceled)
            assert Proforma.objects.all().count() == 5
            assert Invoice.objects.all().count() == 0

            assert Subscription.objects.filter(state='ended').count() == 3

            Proforma.objects.all().delete()

            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect 2 Proformas (2 active Subs, 3 ended)
            assert Proforma.objects.all().count() == 2
