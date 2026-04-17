from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Auth (always present)
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('set-language/', views.SetLanguageView.as_view(), name='set_language'),
]

if views._LICITACIONES:
    urlpatterns += [
        path('tenders/', views.LicitacionsListView.as_view(), name='licitacions_list'),
        path('tenders/<int:pk>/', views.LicitacioDetailView.as_view(), name='licitacio_detail'),
        path('tenders/<int:pk>/informe/nou/', views.InformeCreateView.as_view(), name='informe_create'),
        path('informes/<int:pk>/', views.InformeDetailView.as_view(), name='informe_detail'),
        path('informes/<int:pk>/imprimir/', views.InformePrintView.as_view(), name='informe_print'),
        path('admin-portal/territories/', views.TerritorisView.as_view(), name='territoris'),
        path('admin-portal/territories/contacte/nou/', views.ContacteCreateView.as_view(), name='contacte_create'),
        path('admin-portal/territories/contacte/<int:pk>/edit/', views.ContacteEditView.as_view(), name='contacte_edit'),
        path('admin-portal/territories/contacte/<int:pk>/delete/', views.ContacteDeleteView.as_view(), name='contacte_delete'),
    ]

if views._RRHH:
    urlpatterns += [
        path('timeclock/', views.FicharView.as_view(), name='fichar'),
        path('timeclock/<int:pk>/edit/', views.FichajeEditView.as_view(), name='fichaje_edit'),
        path('admin-portal/', views.AdminOverviewView.as_view(), name='admin_overview'),
        path('admin-portal/users/', views.UserListView.as_view(), name='admin_users'),
        path('admin-portal/users/new/', views.UserCreateView.as_view(), name='admin_user_create'),
        path('admin-portal/users/<int:pk>/edit/', views.UserEditView.as_view(), name='admin_user_edit'),
        path('admin-portal/hr/', views.RrhhDashboardView.as_view(), name='admin_rrhh'),
        path('admin-portal/hr/<int:pk>/edit/', views.AdminFichajeEditView.as_view(), name='admin_fichaje_edit'),
    ]
