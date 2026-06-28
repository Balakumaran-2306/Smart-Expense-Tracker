from django.contrib import admin
from django.urls import path
from tracker import views

urlpatterns = [
    path('admin/',           admin.site.urls),
    path('',                 views.homepage,      name='home'),
    path('home',             views.homepage,      name='home'),
    path('register',         views.register,      name='register'),
    path('login',            views.loginresponse, name='login'),
    path('logout',           views.logoutresponse,name='logout'),
    path('dashboard/',       views.dashboard,     name='dashboard'),
    path('add/income/',      views.add_income,    name='add_income'),
    path('add/expense/',     views.add_expense,   name='add_expense'),
    path('transactions/',    views.transactions,  name='transactions'),
    path('delete/<int:pk>/', views.delete_txn,    name='delete'),
    path('update/<int:pk>/', views.update_txn,    name='update'),
    path('report/',          views.report,        name='report'),
    path('budget/',          views.budget,        name='budget'),
    path('export/',          views.export_csv,    name='export'),
    path('chart-data/',      views.chart_data,    name='chart_data'),
]
