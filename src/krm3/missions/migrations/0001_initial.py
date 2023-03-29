# Generated by Django 3.2.18 on 2023-03-27 16:15

import django.db.models.deletion
import mptt.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reimbursement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('issue_date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='PaymentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('active', models.BooleanField(default=True)),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='missions.paymentcategory')),
            ],
            options={
                'verbose_name_plural': 'payment categories',
            },
        ),
        migrations.CreateModel(
            name='Mission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.city')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.project')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.resource')),
            ],
        ),
        migrations.CreateModel(
            name='ExpenseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('active', models.BooleanField(default=True)),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='missions.expensecategory')),
            ],
            options={
                'verbose_name_plural': 'expense categories',
            },
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField()),
                ('amount_currency', models.DecimalField(decimal_places=2, help_text='Amount in currency', max_digits=10)),
                ('amount_base', models.DecimalField(blank=True, decimal_places=2, help_text='Amount in EUR', max_digits=10, null=True)),
                ('amount_reimbursement', models.DecimalField(blank=True, decimal_places=2, help_text='Reimbursed amount', max_digits=10, null=True)),
                ('detail', models.CharField(max_length=100)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='missions.expensecategory')),
                ('payment_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='missions.paymentcategory')),
                ('reimbursement', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='missions.reimbursement')),
            ],
        ),
    ]
