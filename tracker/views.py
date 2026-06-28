import csv
import json
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Transaction


def homepage(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'tracker/home.html')


def register(request):
    if request.method == "POST":
        username     = request.POST['username']
        password     = request.POST['userpassword']
        confirm_pass = request.POST.get('confirmpassword', password)

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Username already exists!')
            return render(request, 'tracker/Register.html')
        if len(password) < 4:
            messages.error(request, '❌ Password must be at least 4 characters.')
            return render(request, 'tracker/Register.html')
        if confirm_pass != password:
            messages.error(request, '❌ Passwords do not match!')
            return render(request, 'tracker/Register.html')

        User.objects.create_user(username=username, password=password)
        messages.success(request, '✅ Account created! Please login.')
        return redirect('login')

    return render(request, 'tracker/Register.html')


def loginresponse(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'✅ Welcome back, {username}!')
            return redirect('dashboard')
        else:
            messages.error(request, '❌ Invalid username or password.')
    return render(request, 'tracker/login.html')


def logoutresponse(request):
    logout(request)
    messages.info(request, '🔒 Logged out successfully.')
    return redirect('home')


@login_required
def dashboard(request):
    user_txns     = Transaction.objects.filter(user=request.user)
    total_income  = user_txns.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_expense = user_txns.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    balance       = total_income - total_expense
    recent        = user_txns[:5]
    return render(request, 'tracker/dashboard.html', {
        'total_income':  total_income,
        'total_expense': total_expense,
        'balance':       balance,
        'recent':        recent,
    })


@login_required
def add_income(request):
    if request.method == "POST":
        amount = request.POST['amount']
        source = request.POST['source']
        if not amount or not source:
            messages.error(request, '❌ Please fill in all fields.')
            return render(request, 'tracker/add_income.html')
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, '❌ Enter a valid positive amount.')
            return render(request, 'tracker/add_income.html')
        now = timezone.localtime()
        Transaction.objects.create(
            user=request.user, date=now.date(), time=now.time(),
            transaction_type='income', amount=amount, detail=source,
        )
        messages.success(request, f'✅ Income of ₹{amount:.2f} added!')
        return redirect('transactions')
    return render(request, 'tracker/add_income.html')


@login_required
def add_expense(request):
    CATEGORIES = ['Food', 'Travel', 'Groceries', 'Shopping', 'Bills', 'Health', 'Education', 'Other']
    if request.method == "POST":
        amount   = request.POST['amount']
        category = request.POST['category']
        if not amount or not category:
            messages.error(request, '❌ Please fill in all fields.')
            return render(request, 'tracker/add_expense.html', {'categories': CATEGORIES})
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, '❌ Enter a valid positive amount.')
            return render(request, 'tracker/add_expense.html', {'categories': CATEGORIES})
        now = timezone.localtime()
        Transaction.objects.create(
            user=request.user, date=now.date(), time=now.time(),
            transaction_type='expense', amount=amount, detail=category,
        )
        messages.success(request, f'✅ Expense of ₹{amount:.2f} added!')
        return redirect('transactions')
    return render(request, 'tracker/add_expense.html', {'categories': CATEGORIES})


@login_required
def transactions(request):
    txns        = Transaction.objects.filter(user=request.user)
    filter_type = request.GET.get('type', '')
    keyword     = request.GET.get('keyword', '')
    if filter_type in ('income', 'expense'):
        txns = txns.filter(transaction_type=filter_type)
    if keyword:
        txns = txns.filter(detail__icontains=keyword)
    return render(request, 'tracker/transactions.html', {
        'transactions': txns,
        'filter_type':  filter_type,
        'keyword':      keyword,
    })


@login_required
def delete_txn(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    txn.delete()
    messages.success(request, '🗑️ Transaction deleted.')
    return redirect('transactions')


@login_required
def update_txn(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == "POST":
        try:
            txn.amount = float(request.POST['amount'])
        except ValueError:
            messages.error(request, '❌ Invalid amount.')
            return render(request, 'tracker/update.html', {'txn': txn})
        txn.detail = request.POST['detail']
        txn.save()
        messages.success(request, '✅ Transaction updated!')
        return redirect('transactions')
    return render(request, 'tracker/update.html', {'txn': txn})


@login_required
def report(request):
    expense_by_category = (
        Transaction.objects
        .filter(user=request.user, transaction_type='expense')
        .values('detail').annotate(total=Sum('amount')).order_by('-total')
    )
    all_txns = Transaction.objects.filter(user=request.user)
    monthly  = {}
    for t in all_txns:
        key = t.date.strftime('%b %Y')
        if key not in monthly:
            monthly[key] = {'income': Decimal('0'), 'expense': Decimal('0')}
        monthly[key][t.transaction_type] += t.amount
    return render(request, 'tracker/report.html', {
        'expense_by_category': expense_by_category,
        'monthly':             monthly.items(),
    })


@login_required
def budget(request):
    result = None
    if request.method == "POST":
        try:
            limit = Decimal(request.POST['limit'])
        except Exception:
            messages.error(request, '❌ Enter a valid amount.')
            return render(request, 'tracker/budget.html')
        today = date.today()
        total_expense = (
            Transaction.objects
            .filter(user=request.user, transaction_type='expense',
                    date__month=today.month, date__year=today.year)
            .aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )
        exceeded   = total_expense > limit
        percentage = float(total_expense / limit * 100) if limit > 0 else 0
        result = {
            'limit':         limit,
            'total_expense': total_expense,
            'exceeded':      exceeded,
            'percentage':    min(percentage, 100),
            'month':         today.strftime('%B %Y'),
        }
    return render(request, 'tracker/budget.html', {'result': result})


@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'DATE', 'TIME', 'TYPE', 'AMOUNT', 'DETAIL'])
    for t in Transaction.objects.filter(user=request.user):
        writer.writerow([t.pk, t.date, t.time, t.transaction_type, t.amount, t.detail])
    return response


@login_required
def chart_data(request):
    # 1. Pie — expense by category
    expense_rows = (
        Transaction.objects
        .filter(user=request.user, transaction_type='expense')
        .values('detail').annotate(total=Sum('amount')).order_by('-total')
    )
    pie_labels  = [r['detail'] for r in expense_rows]
    pie_amounts = [float(r['total']) for r in expense_rows]

    # 2. Bar — total income vs expense
    total_income  = Transaction.objects.filter(user=request.user, transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = Transaction.objects.filter(user=request.user, transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0

    # 3. Line — last 6 months
    today = date.today()
    monthly_labels, monthly_income, monthly_expense = [], [], []
    for i in range(5, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year  = today.year + ((today.month - i - 1) // 12)
        monthly_labels.append(date(year, month, 1).strftime('%b %Y'))
        inc = Transaction.objects.filter(user=request.user, transaction_type='income',  date__month=month, date__year=year).aggregate(total=Sum('amount'))['total'] or 0
        exp = Transaction.objects.filter(user=request.user, transaction_type='expense', date__month=month, date__year=year).aggregate(total=Sum('amount'))['total'] or 0
        monthly_income.append(float(inc))
        monthly_expense.append(float(exp))

    return JsonResponse({
        'pie':  {'labels': pie_labels, 'amounts': pie_amounts},
        'bar':  {'income': float(total_income), 'expense': float(total_expense)},
        'line': {'labels': monthly_labels, 'income': monthly_income, 'expense': monthly_expense},
    })
