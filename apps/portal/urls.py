from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Auth (always present)
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('set-language/', views.SetLanguageView.as_view(), name='set_language'),
    path('meu-perfil/', views.MeuPerfilView.as_view(), name='meu_perfil'),
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
    try:
        from modules.licitaciones.scraping.models import ScrapingTemplate
        if hasattr(views, 'ScrapingConfigView'):
            urlpatterns += [
                path('admin-portal/scraping/', views.ScrapingConfigView.as_view(), name='scraping_config'),
            ]
    except ImportError:
        pass

if views._EMPRESA:
    urlpatterns += [
        path('admin-portal/empresa/', views.EmpresaEditView.as_view(), name='empresa_edit'),
    ]

if views._OFERTES:
    urlpatterns += [
        path('ofertes/', views.OfertaListView.as_view(), name='ofertes_list'),
        path('ofertes/nova/', views.OfertaCreateView.as_view(), name='oferta_create'),
        path('ofertes/<int:pk>/', views.OfertaDetailView.as_view(), name='oferta_detail'),
    ]

if views._CALENDARI:
    urlpatterns += [
        path('calendari/', views.CalendariView.as_view(), name='calendari'),
        path('calendari/nou/', views.EsdevenimentCreateView.as_view(), name='esdeveniment_create'),
        path('calendari/<int:pk>/eliminar/', views.EsdevenimentDeleteView.as_view(), name='esdeveniment_delete'),
    ]

if views._MARKETING:
    urlpatterns += [
        path('marketing/', views.MarketingDashboardView.as_view(), name='marketing_dashboard'),
        path('marketing/prospects/', views.ProspectsListView.as_view(), name='prospects_list'),
        path('marketing/prospects/nou/', views.ProspectCreateView.as_view(), name='prospect_create'),
        path('marketing/prospects/importar/', views.ImportarProspectsView.as_view(), name='prospects_importar'),
        path('marketing/prospects/descobrir/', views.DescubrirProspectsView.as_view(), name='descobrir_prospects'),
        path('marketing/prospects/<int:pk>/', views.ProspectDetailView.as_view(), name='prospect_detail'),
        path('marketing/campanyes/', views.CampanyesListView.as_view(), name='campanyes_list'),
        path('marketing/campanyes/nova/', views.CampanyaCreateView.as_view(), name='campanya_create'),
        path('marketing/plantilles/', views.PlantillaEmailListView.as_view(), name='plantilles_list'),
        path('marketing/plantilles/nova/', views.PlantillaEmailCreateView.as_view(), name='plantilla_create'),
        path('marketing/plantilles/<int:pk>/editar/', views.PlantillaEmailEditView.as_view(), name='plantilla_edit'),
    ]

if views._DOCUMENTS:
    urlpatterns += [
        path('documents/', views.DocumentListView.as_view(), name='documents_list'),
        path('documents/pujar/', views.DocumentUploadView.as_view(), name='document_upload'),
        path('documents/<uuid:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    ]

if views._PROSPEC:
    urlpatterns += [
        path('marketing/prospec-intel/', views.ProspeccioIntelView.as_view(), name='prospec_intel'),
    ]

if views._ERP:
    urlpatterns += [
        path('erp/clients/', views.ErpClientListView.as_view(), name='erp_clients'),
        path('erp/clients/nou/', views.ErpClientCreateView.as_view(), name='erp_client_create'),
        path('erp/factures/', views.ErpFacturesListView.as_view(), name='erp_factures'),
        path('erp/factures/nova/', views.ErpFacturaCreateView.as_view(), name='erp_factura_create'),
        path('erp/factures/<int:pk>/', views.ErpFacturaDetailView.as_view(), name='erp_factura_detail'),
        path('erp/factures/<int:pk>/document/', views.ErpFacturaDocumentView.as_view(), name='erp_factura_document'),
        path('erp/analitzar/', views.ErpAnalitzarDocumentView.as_view(), name='erp_analitzar'),
        path('erp/albarans/', views.ErpAlbaransListView.as_view(), name='erp_albarans'),
        path('erp/pedidos/', views.ErpPedidosListView.as_view(), name='erp_pedidos'),
    ]

if views._RAG:
    urlpatterns += [
        path('consulta-ia/', views.RagConsultaView.as_view(), name='rag_consulta'),
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
        path('admin-portal/rols/', views.RolListView.as_view(), name='rols_list'),
        path('admin-portal/rols/nou/', views.RolCreateView.as_view(), name='rol_create'),
        path('admin-portal/rols/<int:pk>/editar/', views.RolEditView.as_view(), name='rol_edit'),
        path('admin-portal/rols/<int:pk>/eliminar/', views.RolDeleteView.as_view(), name='rol_delete'),
    ]
