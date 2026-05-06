import datetime
import logging
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum, Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, DetailView

from core.audit.utils import log_action
from .mixins import PortalLoginMixin, RrhhAccessMixin, AdminAccessMixin, get_profile

try:
    from modules.licitaciones.licitaciones.models import (
        Licitacion, InformeIntern, ConfigEmpresa, ContacteProvincial, PROVINCIES_ESPANYA,
    )
    _LICITACIONES = True
except ImportError:
    _LICITACIONES = False

try:
    from modules.rrhh.rrhh.models import UserProfile, Fichaje
    _RRHH = True
except ImportError:
    _RRHH = False

try:
    from modules.empresa.empresa.models import Empresa as EmpresaModel
    _EMPRESA = True
except ImportError:
    _EMPRESA = False

try:
    from modules.erp.erp.models import Client as ClientERP, Factura, Albara, Pedido as PedidoERP
    _ERP = True
except ImportError:
    _ERP = False


class LoginView(View):
    template_name = 'portal/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('portal:dashboard')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_active:
            login(request, user)
            log_action('LOGIN', user=user, request=request)
            return redirect(request.POST.get('next', 'portal:dashboard'))
        messages.error(request, 'Usuari o contrasenya incorrectes.')
        return render(request, self.template_name, {'username': username})


class LogoutView(View):
    def post(self, request):
        if request.user.is_authenticated:
            log_action('LOGOUT', user=request.user, request=request)
        logout(request)
        return redirect('portal:login')


class MeuPerfilView(PortalLoginMixin, View):
    template_name = 'portal/meu_perfil.html'

    def get(self, request):
        profile = get_profile(request.user)
        return render(request, self.template_name, {
            'profile': profile,
            'edit_user': request.user,
        })

    def post(self, request):
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.save()

        profile = get_profile(user)
        if profile:
            profile.telefon = request.POST.get('telefon', '').strip()
            profile.departament = request.POST.get('departament', '').strip()
            profile.save()

        nova_pass = request.POST.get('password', '').strip()
        if nova_pass:
            confirm = request.POST.get('password_confirm', '').strip()
            if nova_pass != confirm:
                messages.error(request, _('Les contrasenyes no coincideixen.'))
                return redirect('portal:meu_perfil')
            if len(nova_pass) < 8:
                messages.error(request, _('La contrasenya ha de tenir mínim 8 caràcters.'))
                return redirect('portal:meu_perfil')
            user.set_password(nova_pass)
            user.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, _('Contrasenya actualitzada correctament.'))

        log_action('PROFILE_UPDATE', user=user, request=request)
        messages.success(request, _('Perfil actualitzat.'))
        return redirect('portal:meu_perfil')


class DashboardView(PortalLoginMixin, View):
    template_name = 'portal/dashboard.html'

    def get(self, request):
        avui = timezone.now().date()
        profile = get_profile(request.user)

        stats = {}
        ultimes = []
        proximes_termini = []
        config = None
        fav_provs = []
        fav_munis = []
        territoris_licitacions = []
        territoris_count = 0
        territoris_noves = 0

        if _LICITACIONES:
            set_mana = avui - datetime.timedelta(days=7)
            stats = {
                'total': Licitacion.objects.count(),
                'noves': Licitacion.objects.filter(estado=Licitacion.Estado.NUEVA).count(),
                'en_preparacio': Licitacion.objects.filter(estado=Licitacion.Estado.EN_PREPARACION).count(),
                'presentades': Licitacion.objects.filter(estado=Licitacion.Estado.PRESENTADA).count(),
                'noves_setmana': Licitacion.objects.filter(creado_en__date__gte=set_mana).count(),
                'import_total': Licitacion.objects.filter(es_relevante=True).aggregate(
                    total=Sum('importe_base'))['total'] or 0,
            }
            ultimes = Licitacion.objects.select_related('organismo').filter(
                es_relevante=True).order_by('-creado_en')[:8]
            proximes_termini = Licitacion.objects.filter(
                fecha_limite_oferta__gte=timezone.now(),
                estado__in=[
                    Licitacion.Estado.NUEVA,
                    Licitacion.Estado.REVISADA,
                    Licitacion.Estado.EN_PREPARACION,
                ],
            ).order_by('fecha_limite_oferta')[:5]

            config = ConfigEmpresa.get()
            fav_provs = list(config.all_favorites())
            fav_munis = list(config.all_municipis())
            q_territori = Q()
            for p in fav_provs:
                q_territori |= Q(provincia__icontains=p)
            for m in fav_munis:
                q_territori |= Q(municipio__icontains=m)
            if fav_provs or fav_munis:
                territoris_licitacions = (
                    Licitacion.objects
                    .filter(q_territori, es_relevante=True)
                    .order_by('-creado_en')[:5]
                )
                territoris_count = Licitacion.objects.filter(q_territori, es_relevante=True).count()
                territoris_noves = Licitacion.objects.filter(
                    q_territori, estado=Licitacion.Estado.NUEVA).count()

        fichaje_avui = None
        if _RRHH:
            fichaje_avui = Fichaje.objects.filter(user=request.user, data=avui).first()

        return render(request, self.template_name, {
            'stats': stats,
            'ultimes': ultimes,
            'proximes_termini': proximes_termini,
            'profile': profile,
            'fichaje_avui': fichaje_avui,
            'config': config,
            'fav_provs': fav_provs,
            'fav_munis': fav_munis,
            'territoris_licitacions': territoris_licitacions,
            'territoris_count': territoris_count,
            'territoris_noves': territoris_noves,
        })


if _LICITACIONES:
    class LicitacionsListView(PortalLoginMixin, ListView):
        model = Licitacion
        template_name = 'portal/licitacions_list.html'
        context_object_name = 'licitacions'
        paginate_by = 20

        def get_queryset(self):
            qs = Licitacion.objects.select_related('organismo').prefetch_related('informes').order_by('-creado_en')
            q = self.request.GET.get('q', '').strip()
            estat = self.request.GET.get('estat', '')
            provincia = self.request.GET.get('provincia', '')
            import_min = self.request.GET.get('import_min', '')
            import_max = self.request.GET.get('import_max', '')
            territori = self.request.GET.get('territori', '')
            formsubmitted = self.request.GET.get('submitted', '')
            solo_vigent = self.request.GET.get('solo_vigent', '') if formsubmitted else '1'
            if q:
                qs = qs.filter(
                    Q(titulo__icontains=q) | Q(expediente_id__icontains=q) | Q(organismo__nombre__icontains=q))
            if estat:
                qs = qs.filter(estado=estat)
            if provincia:
                qs = qs.filter(provincia__icontains=provincia)
            elif territori:
                config = ConfigEmpresa.get()
                q_t = Q()
                for p in config.all_favorites():
                    q_t |= Q(provincia__icontains=p)
                for m in config.all_municipis():
                    q_t |= Q(municipio__icontains=m)
                if q_t:
                    qs = qs.filter(q_t)
            if import_min:
                qs = qs.filter(importe_base__gte=import_min)
            if import_max:
                qs = qs.filter(importe_base__lte=import_max)
            if solo_vigent == '1':
                qs = qs.filter(fecha_limite_oferta__gte=timezone.now())
            return qs

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['estats'] = Licitacion.Estado.choices
            ctx['filtres'] = self.request.GET
            ctx['profile'] = get_profile(self.request.user)
            config = ConfigEmpresa.get()
            ctx['fav_provs'] = list(config.all_favorites())
            ctx['config'] = config
            return ctx

    class LicitacioDetailView(PortalLoginMixin, DetailView):
        model = Licitacion
        template_name = 'portal/licitacio_detail.html'
        context_object_name = 'licitacio'

        def get_queryset(self):
            return Licitacion.objects.select_related('organismo').prefetch_related('criterios')

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['profile'] = get_profile(self.request.user)
            ctx['informes'] = self.object.informes.select_related('autor').all()
            if self.object.pdf_pliego_s3_key:
                try:
                    from core.storage.utils import get_presigned_url
                    ctx['pdf_url'] = get_presigned_url(self.object.pdf_pliego_s3_key, expiry_seconds=1800)
                except Exception:
                    ctx['pdf_url'] = None
            config = ConfigEmpresa.get()
            prov = self.object.provincia
            muni = self.object.municipio
            fav_set = config.all_favorites()
            muni_set = config.all_municipis()
            is_fav = (
                any(p.lower() in prov.lower() or prov.lower() in p.lower() for p in fav_set)
                if prov else False
            ) or (
                any(m.lower() in muni.lower() or muni.lower() in m.lower() for m in muni_set)
                if muni else False
            )
            ctx['is_prov_favorite'] = is_fav
            if is_fav and prov:
                ctx['contactes_provincia'] = ContacteProvincial.objects.filter(
                    provincia__icontains=prov
                )
            ctx['config'] = config
            return ctx

        def post(self, request, pk):
            licitacio = get_object_or_404(Licitacion, pk=pk)
            nou_estat = request.POST.get('estat')
            if nou_estat in Licitacion.Estado.values:
                antic = licitacio.estado
                licitacio.estado = nou_estat
                licitacio.save(update_fields=['estado', 'actualizado_en'])
                log_action('UPDATE', model_name='Licitacion', object_id=str(pk),
                           object_repr=str(licitacio), changes={'estado': [antic, nou_estat]}, request=request)
                messages.success(request, f'Estat actualitzat a {licitacio.get_estado_display()}.')
            return redirect('portal:licitacio_detail', pk=pk)

    class InformeCreateView(PortalLoginMixin, View):
        template_name = 'portal/informe_form.html'

        def get(self, request, pk):
            licitacio = get_object_or_404(Licitacion, pk=pk)
            return render(request, self.template_name, {
                'licitacio': licitacio,
                'recomendacions': InformeIntern.Recomendacio.choices,
                'profile': get_profile(request.user),
            })

        def post(self, request, pk):
            licitacio = get_object_or_404(Licitacion, pk=pk)
            puntuacio_raw = request.POST.get('puntuacio', '').strip()
            informe = InformeIntern.objects.create(
                licitacion=licitacio,
                autor=request.user,
                recomendacio=request.POST.get('recomendacio', InformeIntern.Recomendacio.ESTUDIAR),
                puntuacio=int(puntuacio_raw) if puntuacio_raw.isdigit() else None,
                analisi_tecnica=request.POST.get('analisi_tecnica', '').strip(),
                punts_forts=request.POST.get('punts_forts', '').strip(),
                punts_febles=request.POST.get('punts_febles', '').strip(),
                observacions=request.POST.get('observacions', '').strip(),
            )
            log_action('CREATE', model_name='InformeIntern', object_id=str(informe.pk),
                       object_repr=str(informe), request=request)
            _TRACE_STATES = {'PRESENTADA', 'ADJUDICADA', 'DESIERTA'}
            if licitacio.estado in _TRACE_STATES:
                try:
                    from modules.licitaciones.licitaciones.tasks import generar_pdf_informe
                    generar_pdf_informe.delay(informe.pk)
                except Exception:
                    pass
            messages.success(request, 'Informe intern creat correctament.')
            return redirect('portal:informe_detail', pk=informe.pk)

    class InformeDetailView(PortalLoginMixin, DetailView):
        model = InformeIntern
        template_name = 'portal/informe_detail.html'
        context_object_name = 'informe'

        def get_queryset(self):
            return InformeIntern.objects.select_related('licitacion__organismo', 'autor')

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['profile'] = get_profile(self.request.user)
            if self.object.pdf_s3_key:
                try:
                    from core.storage.utils import get_presigned_url
                    ctx['informe_pdf_url'] = get_presigned_url(
                        self.object.pdf_s3_key, expiry_seconds=1800
                    )
                except Exception:
                    ctx['informe_pdf_url'] = None
            return ctx

    class InformePrintView(PortalLoginMixin, DetailView):
        model = InformeIntern
        template_name = 'portal/informe_print.html'
        context_object_name = 'informe'

        def get_queryset(self):
            return InformeIntern.objects.select_related('licitacion__organismo', 'autor')

    class TerritorisView(AdminAccessMixin, View):
        template_name = 'portal/admin/territoris.html'

        def _get_context(self, request):
            config = ConfigEmpresa.get()
            fav_set = set(config.provincies_favorites)
            contacts = list(ContacteProvincial.objects.all())
            count_map = {}
            for c in contacts:
                count_map[c.provincia] = count_map.get(c.provincia, 0) + 1

            provincies_data = {}
            for comunitat, provs in PROVINCIES_ESPANYA.items():
                provincies_data[comunitat] = [
                    {
                        'nom': p,
                        'is_principal': p == config.provincia_principal,
                        'is_fav': p in fav_set,
                        'contact_count': count_map.get(p, 0),
                    }
                    for p in provs
                ]

            all_provs = sorted({p for provs in PROVINCIES_ESPANYA.values() for p in provs})
            return {
                'config': config,
                'provincies_data': provincies_data,
                'contacts': contacts,
                'rols': ContacteProvincial.Rol.choices,
                'all_provs': all_provs,
                'profile': get_profile(request.user),
            }

        def get(self, request):
            return render(request, self.template_name, self._get_context(request))

        def post(self, request):
            config = ConfigEmpresa.get()
            config.provincia_principal = request.POST.get('provincia_principal', '').strip()
            config.provincies_favorites = request.POST.getlist('provincies_favorites')
            munis_raw = request.POST.get('municipis_favorites_raw', '')
            config.municipis_favorites = [m.strip() for m in munis_raw.split(',') if m.strip()]
            config.save()
            log_action('UPDATE', model_name='ConfigEmpresa', object_id='1',
                       object_repr='Configuració empresa', request=request)
            messages.success(request, 'Preferències territorials desades.')
            return redirect('portal:territoris')

    class ContacteCreateView(AdminAccessMixin, View):
        def post(self, request):
            nom = request.POST.get('nom', '').strip()
            provincia = request.POST.get('provincia', '').strip()
            if nom and provincia:
                ContacteProvincial.objects.create(
                    provincia=provincia,
                    nom=nom,
                    empresa=request.POST.get('empresa', '').strip(),
                    rol=request.POST.get('rol', ContacteProvincial.Rol.ALTRE),
                    telefon=request.POST.get('telefon', '').strip(),
                    email=request.POST.get('email', '').strip(),
                    notes=request.POST.get('notes', '').strip(),
                )
                messages.success(request, f'Contacte "{nom}" afegit.')
            else:
                messages.error(request, 'El nom i la província son obligatoris.')
            return redirect('portal:territoris')

    class ContacteEditView(AdminAccessMixin, View):
        def post(self, request, pk):
            contacte = get_object_or_404(ContacteProvincial, pk=pk)
            nom = request.POST.get('nom', '').strip()
            provincia = request.POST.get('provincia', '').strip()
            if nom and provincia:
                contacte.nom = nom
                contacte.provincia = provincia
                contacte.empresa = request.POST.get('empresa', '').strip()
                contacte.rol = request.POST.get('rol', contacte.rol)
                contacte.telefon = request.POST.get('telefon', '').strip()
                contacte.email = request.POST.get('email', '').strip()
                contacte.notes = request.POST.get('notes', '').strip()
                contacte.save()
                messages.success(request, f'Contacte "{nom}" actualitzat.')
            else:
                messages.error(request, 'El nom i la província son obligatoris.')
            return redirect('portal:territoris')

    class ContacteDeleteView(AdminAccessMixin, View):
        def post(self, request, pk):
            contacte = get_object_or_404(ContacteProvincial, pk=pk)
            nom = contacte.nom
            contacte.delete()
            messages.success(request, f'Contacte "{nom}" eliminat.')
            return redirect('portal:territoris')


# ─── Fitxatge (requires rrhh module) ─────────────────────────────────────────

if _RRHH:
    class FicharView(PortalLoginMixin, View):
        template_name = 'portal/fichar.html'

        def get(self, request):
            avui = timezone.now().date()
            fichaje_avui = Fichaje.objects.filter(user=request.user, data=avui).first()
            ultims = Fichaje.objects.filter(user=request.user).order_by('-data')[:10]
            return render(request, self.template_name, {
                'fichaje_avui': fichaje_avui,
                'ultims': ultims,
                'profile': get_profile(request.user),
                'ara': timezone.now(),
            })

        def post(self, request):
            accio = request.POST.get('accio')
            ara = timezone.now()
            avui = ara.date()
            fichaje, _ = Fichaje.objects.get_or_create(user=request.user, data=avui)

            if accio == 'entrada' and not fichaje.entrada:
                fichaje.entrada = ara
                fichaje.save(update_fields=['entrada'])
                log_action('UPDATE', model_name='Fichaje', object_id=str(fichaje.pk),
                           object_repr=f'Entrada {request.user.username}', request=request)
                messages.success(request, f'Entrada registrada a les {ara.strftime("%H:%M")}.')
            elif accio == 'sortida' and fichaje.entrada and not fichaje.sortida:
                fichaje.sortida = ara
                fichaje.save(update_fields=['sortida'])
                log_action('UPDATE', model_name='Fichaje', object_id=str(fichaje.pk),
                           object_repr=f'Sortida {request.user.username}', request=request)
                messages.success(request, f'Sortida registrada a les {ara.strftime("%H:%M")}.')
            else:
                messages.warning(request, 'No s\'ha pogut registrar el fitxatge.')

            return redirect('portal:fichar')

    class FichajeEditView(PortalLoginMixin, View):
        template_name = 'portal/fichaje_edit.html'

        def get(self, request, pk):
            fichaje = get_object_or_404(Fichaje, pk=pk, user=request.user)
            return render(request, self.template_name, {
                'fichaje': fichaje,
                'profile': get_profile(request.user),
            })

        def post(self, request, pk):
            fichaje = get_object_or_404(Fichaje, pk=pk, user=request.user)
            try:
                entrada_str = request.POST.get('entrada', '').strip()
                sortida_str = request.POST.get('sortida', '').strip()
                if entrada_str:
                    fichaje.entrada = datetime.datetime.fromisoformat(entrada_str).replace(
                        tzinfo=timezone.get_current_timezone())
                if sortida_str:
                    fichaje.sortida = datetime.datetime.fromisoformat(sortida_str).replace(
                        tzinfo=timezone.get_current_timezone())
                else:
                    fichaje.sortida = None
                fichaje.save()
                log_action('UPDATE', model_name='Fichaje', object_id=str(fichaje.pk),
                           object_repr=f'Edit {request.user.username} {fichaje.data}', request=request)
                messages.success(request, 'Fitxatge actualitzat.')
            except Exception as e:
                messages.error(request, f'Error: {e}')
            return redirect('portal:fichar')

    class AdminFichajeEditView(RrhhAccessMixin, View):
        template_name = 'portal/fichaje_edit.html'

        def get(self, request, pk):
            fichaje = get_object_or_404(Fichaje, pk=pk)
            return render(request, self.template_name, {
                'fichaje': fichaje,
                'profile': get_profile(request.user),
                'is_admin_edit': True,
            })

        def post(self, request, pk):
            fichaje = get_object_or_404(Fichaje, pk=pk)
            try:
                entrada_str = request.POST.get('entrada', '').strip()
                sortida_str = request.POST.get('sortida', '').strip()
                if entrada_str:
                    fichaje.entrada = datetime.datetime.fromisoformat(entrada_str).replace(
                        tzinfo=timezone.get_current_timezone())
                if sortida_str:
                    fichaje.sortida = datetime.datetime.fromisoformat(sortida_str).replace(
                        tzinfo=timezone.get_current_timezone())
                else:
                    fichaje.sortida = None
                fichaje.save()
                log_action('UPDATE', model_name='Fichaje', object_id=str(fichaje.pk),
                           object_repr=f'Admin edit {fichaje.user.username} {fichaje.data}', request=request)
                messages.success(request, 'Fitxatge actualitzat.')
            except Exception as e:
                messages.error(request, f'Error: {e}')
            return redirect('portal:admin_rrhh')

    class AdminOverviewView(RrhhAccessMixin, View):
        template_name = 'portal/admin/overview.html'

        def get(self, request):
            profile = get_profile(request.user)
            avui = timezone.now().date()
            set_mana = avui - datetime.timedelta(days=7)

            total_users = User.objects.filter(is_active=True).count()
            users_per_rol = UserProfile.objects.values('role').annotate(total=Count('id')).order_by('role')

            fitxats_avui = Fichaje.objects.filter(data=avui).select_related('user__profile')
            en_oficina = fitxats_avui.filter(entrada__isnull=False, sortida__isnull=True).count()
            sortits_avui = fitxats_avui.filter(sortida__isnull=False).count()

            licitacio_stats = {}
            if _LICITACIONES:
                licitacio_stats = {
                    'noves': Licitacion.objects.filter(estado=Licitacion.Estado.NUEVA).count(),
                    'en_prep': Licitacion.objects.filter(estado=Licitacion.Estado.EN_PREPARACION).count(),
                    'noves_setmana': Licitacion.objects.filter(creado_en__date__gte=set_mana).count(),
                }

            return render(request, self.template_name, {
                'profile': profile,
                'total_users': total_users,
                'users_per_rol': users_per_rol,
                'en_oficina': en_oficina,
                'sortits_avui': sortits_avui,
                'fitxats_avui': fitxats_avui.order_by('-entrada')[:10],
                'licitacio_stats': licitacio_stats,
            })

    class UserListView(AdminAccessMixin, View):
        template_name = 'portal/admin/users.html'

        def get(self, request):
            users = User.objects.select_related('profile').exclude(
                username='n8n-service').order_by('first_name', 'last_name', 'username')
            return render(request, self.template_name, {
                'users': users,
                'roles': UserProfile.Role.choices,
                'profile': get_profile(request.user),
            })

    class UserCreateView(AdminAccessMixin, View):
        template_name = 'portal/admin/user_form.html'

        def get(self, request):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            return render(request, self.template_name, {
                'roles': UserProfile.Role.choices,
                'rols_custom': RolPersonalitzat.objects.all(),
                'profile': get_profile(request.user),
                'action': 'Nou usuari',
            })

        def post(self, request):
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')
            role = request.POST.get('role', UserProfile.Role.TRABAJADOR)
            departament = request.POST.get('departament', '').strip()
            telefon = request.POST.get('telefon', '').strip()
            data_alta = request.POST.get('data_alta') or None

            if not username or not password:
                messages.error(request, 'El nom d\'usuari i la contrasenya son obligatoris.')
                return render(request, self.template_name, {
                    'roles': UserProfile.Role.choices,
                    'profile': get_profile(request.user),
                    'action': 'Nou usuari',
                    'data': request.POST,
                })

            if User.objects.filter(username=username).exists():
                messages.error(request, f'L\'usuari "{username}" ja existeix.')
                from modules.rrhh.rrhh.models import RolPersonalitzat
                return render(request, self.template_name, {
                    'roles': UserProfile.Role.choices,
                    'rols_custom': RolPersonalitzat.objects.all(),
                    'profile': get_profile(request.user),
                    'action': 'Nou usuari',
                    'data': request.POST,
                })

            user = User.objects.create_user(
                username=username, first_name=first_name, last_name=last_name,
                email=email, password=password,
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.departament = departament
            profile.telefon = telefon
            profile.data_alta = data_alta
            rol_custom_id = request.POST.get('rol_custom_id') or None
            if rol_custom_id:
                try:
                    from modules.rrhh.rrhh.models import RolPersonalitzat
                    profile.rol_custom = RolPersonalitzat.objects.get(pk=rol_custom_id)
                except Exception:
                    pass
            profile.save()

            log_action('CREATE', model_name='User', object_id=str(user.pk),
                       object_repr=username, request=request)
            messages.success(request, f'Usuari "{username}" creat correctament.')
            return redirect('portal:admin_users')

    class UserEditView(AdminAccessMixin, View):
        template_name = 'portal/admin/user_form.html'

        def get(self, request, pk):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            user = get_object_or_404(User, pk=pk)
            profile = get_profile(user)
            return render(request, self.template_name, {
                'edit_user': user,
                'edit_profile': profile,
                'roles': UserProfile.Role.choices,
                'rols_custom': RolPersonalitzat.objects.all(),
                'profile': get_profile(request.user),
                'action': f'Editar {user.username}',
            })

        def post(self, request, pk):
            user = get_object_or_404(User, pk=pk)
            profile = get_profile(user)

            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            actiu = request.POST.get('actiu') == 'on'
            user.is_active = actiu
            user.save()

            profile.role = request.POST.get('role', profile.role)
            profile.departament = request.POST.get('departament', '').strip()
            profile.telefon = request.POST.get('telefon', '').strip()
            profile.data_alta = request.POST.get('data_alta') or None
            profile.notes = request.POST.get('notes', '').strip()
            profile.actiu = actiu
            rol_custom_id = request.POST.get('rol_custom_id') or None
            if rol_custom_id:
                try:
                    from modules.rrhh.rrhh.models import RolPersonalitzat
                    profile.rol_custom = RolPersonalitzat.objects.get(pk=rol_custom_id)
                except Exception:
                    profile.rol_custom = None
            else:
                profile.rol_custom = None
            profile.save()

            nova_pass = request.POST.get('password', '').strip()
            if nova_pass:
                user.set_password(nova_pass)
                user.save()

            log_action('UPDATE', model_name='User', object_id=str(user.pk),
                       object_repr=user.username, request=request)
            messages.success(request, f'Usuari "{user.username}" actualitzat.')
            return redirect('portal:admin_users')

    class RolListView(AdminAccessMixin, View):
        template_name = 'portal/admin/rols.html'

        def get(self, request):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            permisos_dict = dict(RolPersonalitzat.PERMISOS_DISPONIBLES)
            rols_raw = RolPersonalitzat.objects.all()
            rols = []
            for rol in rols_raw:
                permisos = [
                    {'key': key, 'label': label, 'actiu': rol.te_permis(key)}
                    for key, label in RolPersonalitzat.PERMISOS_DISPONIBLES
                ]
                rols.append({'rol': rol, 'permisos': permisos})
            return render(request, self.template_name, {
                'rols': rols,
                'rols_base': UserProfile.Role.choices,
                'permisos_disponibles': RolPersonalitzat.PERMISOS_DISPONIBLES,
                'profile': get_profile(request.user),
            })

    class RolCreateView(AdminAccessMixin, View):
        template_name = 'portal/admin/rol_form.html'

        def get(self, request):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            return render(request, self.template_name, {
                'permisos_disponibles': RolPersonalitzat.PERMISOS_DISPONIBLES,
                'permisos_per_modul': RolPersonalitzat.PERMISOS_PER_MODUL,
                'permisos_actius': set(),
                'profile': get_profile(request.user),
                'action': _('Nou rol'),
            })

        def post(self, request):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            nom = request.POST.get('nom', '').strip()
            if not nom:
                messages.error(request, _('El nom del rol és obligatori.'))
                return redirect('portal:rols_list')
            permisos = {
                key: request.POST.get(key) == 'on'
                for key, _ in RolPersonalitzat.PERMISOS_DISPONIBLES
            }
            RolPersonalitzat.objects.create(
                nom=nom,
                descripcio=request.POST.get('descripcio', '').strip(),
                permisos=permisos,
            )
            messages.success(request, _('Rol creat correctament.'))
            return redirect('portal:rols_list')

    class RolEditView(AdminAccessMixin, View):
        template_name = 'portal/admin/rol_form.html'

        def get(self, request, pk):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            rol = get_object_or_404(RolPersonalitzat, pk=pk)
            permisos_actius = {key for key, _ in RolPersonalitzat.PERMISOS_DISPONIBLES if rol.te_permis(key)}
            return render(request, self.template_name, {
                'rol': rol,
                'permisos_disponibles': RolPersonalitzat.PERMISOS_DISPONIBLES,
                'permisos_per_modul': RolPersonalitzat.PERMISOS_PER_MODUL,
                'permisos_actius': permisos_actius,
                'profile': get_profile(request.user),
                'action': _('Editar rol'),
            })

        def post(self, request, pk):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            rol = get_object_or_404(RolPersonalitzat, pk=pk)
            nom = request.POST.get('nom', '').strip()
            if not nom:
                messages.error(request, _('El nom del rol és obligatori.'))
                return redirect('portal:rol_edit', pk=pk)
            rol.nom = nom
            rol.descripcio = request.POST.get('descripcio', '').strip()
            rol.permisos = {
                key: request.POST.get(key) == 'on'
                for key, _ in RolPersonalitzat.PERMISOS_DISPONIBLES
            }
            rol.save()
            messages.success(request, _('Rol actualitzat.'))
            return redirect('portal:rols_list')

    class RolDeleteView(AdminAccessMixin, View):
        def post(self, request, pk):
            from modules.rrhh.rrhh.models import RolPersonalitzat
            rol = get_object_or_404(RolPersonalitzat, pk=pk)
            nom = rol.nom
            rol.delete()
            messages.success(request, _(f'Rol "{nom}" eliminat.'))
            return redirect('portal:rols_list')

    class RrhhDashboardView(RrhhAccessMixin, View):
        template_name = 'portal/admin/rrhh.html'

        def get(self, request):
            profile = get_profile(request.user)
            avui = timezone.now().date()

            data_str = request.GET.get('data', '')
            try:
                data_filtre = datetime.date.fromisoformat(data_str) if data_str else avui
            except ValueError:
                data_filtre = avui

            fitxatges = Fichaje.objects.filter(
                data=data_filtre
            ).select_related('user__profile').order_by('entrada')

            dilluns = data_filtre - datetime.timedelta(days=data_filtre.weekday())
            diumenge = dilluns + datetime.timedelta(days=6)
            fitxatges_setmana = Fichaje.objects.filter(
                data__range=(dilluns, diumenge)
            ).select_related('user')

            totals = {}
            for f in fitxatges_setmana:
                stats = totals.setdefault(f.user_id, {'user': f.user, 'dies': 0, 'hores': 0.0})
                stats['dies'] += 1
                stats['hores'] += float(f.hores_treballades or 0)
            resum_setmana = list(totals.values())

            users_actius = User.objects.filter(
                is_active=True, profile__actiu=True
            ).select_related('profile').order_by('first_name')

            return render(request, self.template_name, {
                'profile': profile,
                'data_filtre': data_filtre,
                'fitxatges': fitxatges,
                'fitxatges_setmana': fitxatges_setmana,
                'resum_setmana': resum_setmana,
                'users_actius': users_actius,
                'avui': avui,
                'dilluns': dilluns,
                'diumenge': diumenge,
            })


# ─── Scraping Configuration ──────────────────────────────────────────────────

if _LICITACIONES:
    try:
        from modules.licitaciones.scraping.models import ScrapingTemplate
        _SCRAPING = True
    except ImportError:
        _SCRAPING = False

    if _SCRAPING:
        class ScrapingConfigView(AdminAccessMixin, View):
            template_name = 'portal/admin/scraping_config.html'

            def get(self, request):
                template = ScrapingTemplate.get_singleton()
                from modules.licitaciones.licitaciones.models import PROVINCIES_ESPANYA

                all_provs = []
                all_munis = set()
                for provs in PROVINCIES_ESPANYA.values():
                    all_provs.extend(provs)
                all_provs = sorted(set(all_provs))

                try:
                    from modules.licitaciones.licitaciones.models import Licitacion
                    all_munis = sorted(set(
                        Licitacion.objects.values_list('municipio', flat=True)
                        .filter(municipio__isnull=False)
                        .exclude(municipio='')
                    ))
                except Exception:
                    all_munis = []

                return render(request, self.template_name, {
                    'template': template,
                    'profile': get_profile(request.user),
                    'provincias_list': all_provs,
                    'municipios_list': all_munis,
                    'tipo_choices': [
                        ('1', 'Obras'),
                        ('2', 'Concesión Obras'),
                        ('3', 'Gestión Servicios'),
                        ('4', 'Suministros'),
                        ('5', 'Servicios'),
                        ('6', 'Otros'),
                    ],
                    'procediment_choices': [
                        ('1', 'Abierto'),
                        ('2', 'Restringido'),
                        ('4', 'Negociado s/publicidad'),
                        ('7', 'Simplificado'),
                    ],
                })

            def post(self, request):
                template = ScrapingTemplate.get_singleton()

                template.nom = request.POST.get('nom', '').strip() or 'Default'
                template.activa = request.POST.get('activa') == 'on'

                importe_min = request.POST.get('importe_min', '').strip()
                importe_max = request.POST.get('importe_max', '').strip()
                template.importe_min = float(importe_min) if importe_min else None
                template.importe_max = float(importe_max) if importe_max else None

                max_pagines = request.POST.get('max_pagines', '10').strip()
                template.max_pagines = int(max_pagines) if max_pagines.isdigit() else 10

                template.provincies = request.POST.getlist('provincies')
                template.municipis = request.POST.getlist('municipis')
                template.tipus_contracte = request.POST.getlist('tipus_contracte')
                template.procediments = request.POST.getlist('procediments')

                cpv_raw = request.POST.get('cpv_raw', '').strip()
                if cpv_raw:
                    cpv_list = [c.strip() for c in cpv_raw.split('\n') if c.strip()]
                    template.cpv_inclosos = cpv_list
                else:
                    template.cpv_inclosos = []

                try:
                    template.save()
                    log_action('UPDATE', model_name='ScrapingTemplate', object_id=str(template.pk),
                               object_repr='ScrapingTemplate', request=request)
                    messages.success(request, 'Configuració de scraping actualitzada.')
                except Exception as e:
                    messages.error(request, f'Error: {e}')

                return redirect('portal:scraping_config')


# ─── Empresa config ──────────────────────────────────────────────────────────

if _EMPRESA:
    class EmpresaEditView(AdminAccessMixin, View):
        template_name = 'portal/admin/empresa.html'

        def get(self, request):
            empresa = EmpresaModel.get()
            return render(request, self.template_name, {
                'empresa': empresa,
                'profile': get_profile(request.user),
            })

        def post(self, request):
            empresa = EmpresaModel.get()
            empresa.nombre_empresa = request.POST.get('nombre_empresa', '').strip() or empresa.nombre_empresa
            empresa.direccion = request.POST.get('direccion', '').strip()
            empresa.ciudad = request.POST.get('ciudad', '').strip()
            empresa.pais = request.POST.get('pais', '').strip() or 'España'
            empresa.email_contacto = request.POST.get('email_contacto', '').strip()
            empresa.telefono = request.POST.get('telefono', '').strip()
            empresa.descripcion = request.POST.get('descripcion', '').strip()

            if 'logo' in request.FILES:
                if empresa.logo:
                    empresa.logo.delete(save=False)
                empresa.logo = request.FILES['logo']
            elif request.POST.get('logo_clear') == '1' and empresa.logo:
                empresa.logo.delete(save=False)
                empresa.logo = None

            empresa.save()
            log_action('UPDATE', model_name='Empresa', object_id='1',
                       object_repr=empresa.nombre_empresa, request=request)
            messages.success(request, _('Datos de empresa actualizados correctamente.'))
            return redirect('portal:empresa_edit')


# ─── Language switch (always available) ──────────────────────────────────────

class SetLanguageView(View):
    def post(self, request):
        lang = request.POST.get('language', 'es')
        allowed = [code for code, _ in django_settings.LANGUAGES]
        if lang in allowed:
            request.session['django_language'] = lang
            from django.utils.translation import activate
            activate(lang)
            response = redirect(request.META.get('HTTP_REFERER', '/portal/'))
            response.set_cookie(django_settings.LANGUAGE_COOKIE_NAME, lang)
            return response
        return redirect('/portal/')


# ─── Optional module flags ─────────────────────────────────────────────────────

try:
    from modules.ofertes.ofertes.models import Oferta, Pressupost, LiniaPressupost, PlaSeguretat
    _OFERTES = True
except ImportError:
    _OFERTES = False

try:
    from modules.calendari.calendari.models import CalendariConfig, Esdeveniment
    _CALENDARI = True
except ImportError:
    _CALENDARI = False

try:
    from modules.marketing.marketing.models import EmpresaProspect, CampanyaMarketing, PlantillaEmail, EnviamentEmail
    _MARKETING = True
except ImportError:
    _MARKETING = False

try:
    from modules.documents.documents.models import Document, CategoriaDocument, VersioDocument, AccesDocument
    _DOCUMENTS = True
except ImportError:
    _DOCUMENTS = False

try:
    from modules.rag.rag.models import ConsultaRAG
    _RAG = True
except ImportError:
    _RAG = False

try:
    from modules.prospec.prospec.registry import cercar_tots as _prospec_cercar
    from modules.prospec.prospec import sources as _prospec_sources_loaded  # noqa: F401 triggers registration
    _PROSPEC = True
except ImportError:
    _PROSPEC = False


# ─── Ofertes i Pressupostos ───────────────────────────────────────────────────

if _OFERTES:
    class OfertaListView(PortalLoginMixin, View):
        template_name = 'portal/ofertes/oferta_list.html'

        def get(self, request):
            profile = get_profile(request.user)
            qs = Oferta.objects.select_related('licitacio', 'responsable').order_by('-creada_en')
            q = request.GET.get('q', '').strip()
            estat = request.GET.get('estat', '')
            risc = request.GET.get('risc', '')
            if q:
                qs = qs.filter(licitacio__titol__icontains=q)
            if estat:
                qs = qs.filter(estat=estat)
            if risc:
                qs = qs.filter(nivell_risc=risc)
            estats = Oferta.Estat.choices
            riscs = Oferta.NivellRisc.choices
            return render(request, self.template_name, {
                'ofertes': qs,
                'estats': estats,
                'riscs': riscs,
                'filtres': {'q': q, 'estat': estat, 'risc': risc},
                'profile': profile,
            })

    class OfertaDetailView(PortalLoginMixin, View):
        template_name = 'portal/ofertes/oferta_detail.html'

        def get(self, request, pk):
            profile = get_profile(request.user)
            oferta = get_object_or_404(Oferta.objects.select_related('licitacio', 'responsable', 'revisor'), pk=pk)
            pressupost = Pressupost.objects.filter(oferta=oferta).prefetch_related('linies').first()
            pla = getattr(oferta, 'pla_seguretat', None)
            versions = oferta.versions.order_by('-creada_en')[:5]
            return render(request, self.template_name, {
                'oferta': oferta,
                'pressupost': pressupost,
                'pla': pla,
                'versions': versions,
                'estats': Oferta.Estat.choices,
                'profile': profile,
            })

        def post(self, request, pk):
            oferta = get_object_or_404(Oferta, pk=pk)
            action = request.POST.get('action', '')
            if action == 'canviar_estat':
                nou_estat = request.POST.get('estat', '')
                try:
                    oferta.transicionar_estat(nou_estat)
                    messages.success(request, _('Estat actualitzat correctament.'))
                except ValueError as e:
                    messages.error(request, str(e))
            elif action == 'desar_notes':
                oferta.notes_internes = request.POST.get('notes_internes', '')
                oferta.justificacio_preu = request.POST.get('justificacio_preu', '')
                oferta.save(update_fields=['notes_internes', 'justificacio_preu'])
                messages.success(request, _('Notes desades correctament.'))
            elif action == 'calcular_preu':
                try:
                    from modules.ofertes.ofertes.tasks import calcular_preu_optim_task
                    calcular_preu_optim_task.delay(pk)
                    messages.info(request, _('Càlcul de preu òptim llançat en segon pla.'))
                except Exception:
                    messages.error(request, _('Error llançant el càlcul.'))
            elif action == 'generar_pss':
                try:
                    from modules.ofertes.ofertes.tasks import generar_pla_seguretat_ia
                    generar_pla_seguretat_ia.delay(pk)
                    messages.info(request, _('Generació del Pla de Seguretat llançada en segon pla.'))
                except Exception:
                    messages.error(request, _('Error llançant la generació.'))
            return redirect('portal:oferta_detail', pk=pk)

    class OfertaCreateView(PortalLoginMixin, View):
        template_name = 'portal/ofertes/oferta_form.html'

        def get(self, request):
            profile = get_profile(request.user)
            licitacions_disponibles = []
            if _LICITACIONES:
                licitacions_disponibles = Licitacion.objects.filter(
                    oferta__isnull=True,
                    estado__in=['EN_PREPARACION', 'REVISADA'],
                ).order_by('-creado_en')
            users = User.objects.filter(is_active=True).order_by('first_name')
            return render(request, self.template_name, {
                'licitacions_disponibles': licitacions_disponibles,
                'users': users,
                'profile': profile,
            })

        def post(self, request):
            licitacio_pk = request.POST.get('licitacio_id')
            responsable_id = request.POST.get('responsable_id')
            if not licitacio_pk:
                messages.error(request, _('Cal seleccionar una licitació.'))
                return redirect('portal:oferta_create')
            try:
                from modules.ofertes.ofertes.services import crear_oferta_des_de_licitacio
                oferta = crear_oferta_des_de_licitacio(int(licitacio_pk))
                if responsable_id:
                    oferta.responsable_id = responsable_id
                    oferta.save(update_fields=['responsable'])
                log_action('OFERTA_CREADA', user=request.user, object_id=oferta.pk,
                           object_repr=str(oferta), request=request)
                messages.success(request, _('Oferta creada correctament.'))
                return redirect('portal:oferta_detail', pk=oferta.pk)
            except Exception as e:
                messages.error(request, str(e))
                return redirect('portal:oferta_create')


# ─── Calendari Laboral ────────────────────────────────────────────────────────

if _CALENDARI:
    class CalendariView(PortalLoginMixin, View):
        template_name = 'portal/calendari/calendari.html'

        def get(self, request):
            profile = get_profile(request.user)
            any_sel = int(request.GET.get('any', timezone.now().year))
            mes_sel = int(request.GET.get('mes', timezone.now().month))
            inici = datetime.date(any_sel, mes_sel, 1)
            if mes_sel == 12:
                fi = datetime.date(any_sel + 1, 1, 1)
            else:
                fi = datetime.date(any_sel, mes_sel + 1, 1)
            fi = fi - datetime.timedelta(days=1)
            esdeveniments = list(Esdeveniment.objects.filter(
                inici__date__gte=inici,
                inici__date__lte=fi,
            ).order_by('inici'))
            config = CalendariConfig.objects.filter(usuari=request.user).first()
            mes_anterior = inici - datetime.timedelta(days=1)
            mes_seguent = fi + datetime.timedelta(days=1)

            # Build calendar grid cells (42 cells = 6 weeks × 7 days, Monday start)
            avui = timezone.now().date()
            events_by_date = {}
            for ev in esdeveniments:
                d = ev.inici.date()
                events_by_date.setdefault(d, []).append(ev)
            dow_first = inici.weekday()  # 0=Mon
            cal_cells = []
            for offset in range(-dow_first, 42 - dow_first):
                d = inici + datetime.timedelta(days=offset)
                cal_cells.append({
                    'date': d,
                    'day': d.day,
                    'current_month': d.month == mes_sel,
                    'is_today': d == avui,
                    'events': events_by_date.get(d, []),
                })

            return render(request, self.template_name, {
                'esdeveniments': esdeveniments,
                'cal_cells': cal_cells,
                'any_sel': any_sel,
                'mes_sel': mes_sel,
                'mes_anterior': mes_anterior,
                'mes_seguent': mes_seguent,
                'inici': inici,
                'fi': fi,
                'config': config,
                'tipus_choices': Esdeveniment.TipusEsdeveniment.choices,
                'profile': profile,
            })

    class EsdevenimentCreateView(PortalLoginMixin, View):
        template_name = 'portal/calendari/esdeveniment_form.html'

        def get(self, request):
            profile = get_profile(request.user)
            licitacions = []
            if _LICITACIONES:
                licitacions = Licitacion.objects.filter(
                    estado__in=['NUEVA', 'REVISADA', 'EN_PREPARACION']
                ).order_by('-creado_en')[:50]
            return render(request, self.template_name, {
                'tipus_choices': Esdeveniment.TipusEsdeveniment.choices,
                'licitacions': licitacions,
                'profile': profile,
            })

        def post(self, request):
            titol = request.POST.get('titol', '').strip()
            tipus = request.POST.get('tipus', '')
            data_inici_str = request.POST.get('data_inici', '')
            data_fi_str = request.POST.get('data_fi', '')
            descripcio = request.POST.get('descripcio', '')
            licitacio_id = request.POST.get('licitacio_id', '') or None
            if not titol or not data_inici_str:
                messages.error(request, _('El títol i la data d\'inici són obligatoris.'))
                return redirect('portal:esdeveniment_create')
            try:
                dt_inici = datetime.datetime.fromisoformat(data_inici_str)
                dt_fi = datetime.datetime.fromisoformat(data_fi_str) if data_fi_str else dt_inici + datetime.timedelta(hours=1)
                ev = Esdeveniment.objects.create(
                    titol=titol,
                    tipus=tipus or Esdeveniment.TipusEsdeveniment.REUNIO_INTERNA,
                    inici=timezone.make_aware(dt_inici) if timezone.is_naive(dt_inici) else dt_inici,
                    fi=timezone.make_aware(dt_fi) if timezone.is_naive(dt_fi) else dt_fi,
                    descripcio=descripcio,
                    licitacio_id=licitacio_id,
                    creador=request.user,
                )
                from modules.calendari.calendari.tasks import sincronitzar_esdeveniment
                sincronitzar_esdeveniment.delay(ev.pk)
                messages.success(request, _('Esdeveniment creat correctament.'))
                return redirect('portal:calendari')
            except Exception as e:
                messages.error(request, str(e))
                return redirect('portal:esdeveniment_create')

    class EsdevenimentDeleteView(PortalLoginMixin, View):
        def post(self, request, pk):
            ev = get_object_or_404(Esdeveniment, pk=pk)
            ev.delete()
            messages.success(request, _('Esdeveniment eliminat.'))
            return redirect('portal:calendari')


# ─── Marketing Automatitzat ───────────────────────────────────────────────────

if _MARKETING:
    class MarketingDashboardView(PortalLoginMixin, View):
        template_name = 'portal/marketing/dashboard.html'

        def get(self, request):
            profile = get_profile(request.user)
            total_prospects = EmpresaProspect.objects.count()
            actius = EmpresaProspect.objects.filter(
                consentiment_gdpr=True, baixa_voluntaria=False
            ).count()
            campanyes_actives = CampanyaMarketing.objects.filter(estat='EN_CURS').count()
            top_prospects = EmpresaProspect.objects.filter(
                consentiment_gdpr=True, baixa_voluntaria=False
            ).order_by('-scoring')[:5]
            ultimes_campanyes = CampanyaMarketing.objects.order_by('-creada_en')[:5]
            return render(request, self.template_name, {
                'total_prospects': total_prospects,
                'actius': actius,
                'campanyes_actives': campanyes_actives,
                'top_prospects': top_prospects,
                'ultimes_campanyes': ultimes_campanyes,
                'profile': profile,
            })

    class ProspectsListView(PortalLoginMixin, View):
        template_name = 'portal/marketing/prospects_list.html'

        def get(self, request):
            profile = get_profile(request.user)
            qs = EmpresaProspect.objects.order_by('-scoring')
            q = request.GET.get('q', '').strip()
            estat = request.GET.get('estat', '')
            sector = request.GET.get('sector', '')
            gdpr = request.GET.get('gdpr', '')
            if q:
                qs = qs.filter(nom__icontains=q)
            if estat:
                qs = qs.filter(estat=estat)
            if sector:
                qs = qs.filter(sector=sector)
            if gdpr == '1':
                qs = qs.filter(consentiment_gdpr=True, baixa_voluntaria=False)
            elif gdpr == '0':
                qs = qs.filter(consentiment_gdpr=False)
            return render(request, self.template_name, {
                'prospects': qs,
                'estats': EmpresaProspect.Estat.choices,
                'sectors': EmpresaProspect.Sector.choices,
                'filtres': {'q': q, 'estat': estat, 'sector': sector, 'gdpr': gdpr},
                'profile': profile,
            })

    class ProspectDetailView(PortalLoginMixin, View):
        template_name = 'portal/marketing/prospect_detail.html'

        def get(self, request, pk):
            profile = get_profile(request.user)
            prospect = get_object_or_404(EmpresaProspect, pk=pk)
            enviaments = EnviamentEmail.objects.filter(
                prospect=prospect
            ).order_by('-enviat_en')[:10]
            return render(request, self.template_name, {
                'prospect': prospect,
                'enviaments': enviaments,
                'estats': EmpresaProspect.Estat.choices,
                'profile': profile,
            })

        def post(self, request, pk):
            prospect = get_object_or_404(EmpresaProspect, pk=pk)
            action = request.POST.get('action', '')
            if action == 'canviar_estat':
                prospect.estat = request.POST.get('estat', prospect.estat)
                prospect.save(update_fields=['estat'])
                messages.success(request, _('Estat actualitzat.'))
            elif action == 'recalcular_scoring':
                from modules.marketing.marketing.services import calcular_scoring_prospect
                prospect.scoring = calcular_scoring_prospect(prospect)
                prospect.save(update_fields=['scoring'])
                messages.success(request, _('Scoring recalculat: {:.1f}/10'.format(prospect.scoring)))
            elif action == 'editar':
                prospect.email_principal = request.POST.get('email_principal', prospect.email_principal).strip()
                prospect.telefon = request.POST.get('telefon', prospect.telefon).strip()
                prospect.web = request.POST.get('web', prospect.web).strip()
                prospect.persona_contacte = request.POST.get('persona_contacte', prospect.persona_contacte).strip()
                prospect.carrec_contacte = request.POST.get('carrec_contacte', prospect.carrec_contacte).strip()
                prospect.poblacio = request.POST.get('poblacio', prospect.poblacio).strip()
                prospect.provincia = request.POST.get('provincia', prospect.provincia).strip()
                prospect.consentiment_gdpr = request.POST.get('consentiment_gdpr') == '1'
                prospect.notes = request.POST.get('notes', prospect.notes).strip()
                from modules.marketing.marketing.services import calcular_scoring_prospect
                prospect.scoring = calcular_scoring_prospect(prospect)
                prospect.save()
                messages.success(request, _('Dades actualitzades.'))
            return redirect('portal:prospect_detail', pk=pk)

    class ProspectCreateView(PortalLoginMixin, View):
        template_name = 'portal/marketing/prospect_form.html'

        def get(self, request):
            profile = get_profile(request.user)
            return render(request, self.template_name, {
                'estats': EmpresaProspect.Estat.choices,
                'sectors': EmpresaProspect.Sector.choices,
                'profile': profile,
            })

        def post(self, request):
            nom = request.POST.get('nom', '').strip()
            if not nom:
                messages.error(request, _('El nom és obligatori.'))
                return redirect('portal:prospect_create')
            p = EmpresaProspect.objects.create(
                nom=nom,
                sector=request.POST.get('sector', 'CONSTRUCCIO'),
                estat=request.POST.get('estat', 'PROSPECCIO'),
                email_principal=request.POST.get('email_principal', ''),
                telefon=request.POST.get('telefon', ''),
                web=request.POST.get('web', ''),
                persona_contacte=request.POST.get('persona_contacte', ''),
                carrec_contacte=request.POST.get('carrec_contacte', ''),
                poblacio=request.POST.get('poblacio', ''),
                provincia=request.POST.get('provincia', ''),
                notes=request.POST.get('notes', ''),
                consentiment_gdpr=bool(request.POST.get('consentiment_gdpr')),
            )
            messages.success(request, _('Prospect creat correctament.'))
            return redirect('portal:prospect_detail', pk=p.pk)

    class CampanyesListView(PortalLoginMixin, View):
        template_name = 'portal/marketing/campanyes_list.html'

        def get(self, request):
            profile = get_profile(request.user)
            campanyes = CampanyaMarketing.objects.order_by('-creada_en')
            return render(request, self.template_name, {
                'campanyes': campanyes,
                'profile': profile,
            })

    class CampanyaCreateView(PortalLoginMixin, View):
        template_name = 'portal/marketing/campanya_form.html'

        def get(self, request):
            profile = get_profile(request.user)
            plantilles = PlantillaEmail.objects.filter(activa=True)
            return render(request, self.template_name, {
                'plantilles': plantilles,
                'sectors': EmpresaProspect.Sector.choices,
                'profile': profile,
            })

        def post(self, request):
            nom = request.POST.get('nom', '').strip()
            plantilla_id = request.POST.get('plantilla_id', '')
            if not nom or not plantilla_id:
                messages.error(request, _('Nom i plantilla són obligatoris.'))
                return redirect('portal:campanya_create')
            segmentacio = {
                'sectors': request.POST.getlist('sectors'),
                'scoring_minim': request.POST.get('scoring_minim', '0'),
                'provincia': request.POST.get('provincia', ''),
            }
            c = CampanyaMarketing.objects.create(
                nom=nom,
                plantilla_id=plantilla_id,
                segments=segmentacio,
                millorar_amb_ia=bool(request.POST.get('millorar_amb_ia')),
                creada_per=request.user,
            )
            messages.success(request, _('Campanya creada. Podeu llançar-la des del detall.'))
            return redirect('portal:campanyes_list')

    class PlantillaEmailListView(PortalLoginMixin, View):
        template_name = 'portal/marketing/plantilles_list.html'

        def get(self, request):
            profile = get_profile(request.user)
            plantilles = PlantillaEmail.objects.order_by('-actualitzada_en')
            return render(request, self.template_name, {
                'plantilles': plantilles,
                'tipus_choices': PlantillaEmail.Tipus.choices,
                'profile': profile,
            })

    class PlantillaEmailCreateView(PortalLoginMixin, View):
        template_name = 'portal/marketing/plantilla_form.html'

        def get(self, request):
            profile = get_profile(request.user)
            return render(request, self.template_name, {
                'plantilla': None,
                'tipus_choices': PlantillaEmail.Tipus.choices,
                'idiomes': [('ca', 'Català'), ('es', 'Español'), ('en', 'English')],
                'profile': profile,
            })

        def post(self, request):
            nom = request.POST.get('nom', '').strip()
            assumpte = request.POST.get('assumpte', '').strip()
            cos_text = request.POST.get('cos_text', '').strip()
            if not nom or not assumpte or not cos_text:
                messages.error(request, _('Nom, assumpte i cos del missatge són obligatoris.'))
                return redirect('portal:plantilla_create')
            PlantillaEmail.objects.create(
                nom=nom,
                tipus=request.POST.get('tipus', 'PROSPECCIO'),
                idioma=request.POST.get('idioma', 'ca'),
                assumpte=assumpte,
                cos_text=cos_text,
                cos_html=request.POST.get('cos_html', ''),
                activa=bool(request.POST.get('activa', True)),
                creada_per=request.user,
            )
            messages.success(request, _('Plantilla creada correctament.'))
            return redirect('portal:plantilles_list')

    class PlantillaEmailEditView(PortalLoginMixin, View):
        template_name = 'portal/marketing/plantilla_form.html'

        def get(self, request, pk):
            profile = get_profile(request.user)
            plantilla = get_object_or_404(PlantillaEmail, pk=pk)
            return render(request, self.template_name, {
                'plantilla': plantilla,
                'tipus_choices': PlantillaEmail.Tipus.choices,
                'idiomes': [('ca', 'Català'), ('es', 'Español'), ('en', 'English')],
                'profile': profile,
            })

        def post(self, request, pk):
            plantilla = get_object_or_404(PlantillaEmail, pk=pk)
            plantilla.nom = request.POST.get('nom', plantilla.nom).strip()
            plantilla.tipus = request.POST.get('tipus', plantilla.tipus)
            plantilla.idioma = request.POST.get('idioma', plantilla.idioma)
            plantilla.assumpte = request.POST.get('assumpte', plantilla.assumpte).strip()
            plantilla.cos_text = request.POST.get('cos_text', plantilla.cos_text)
            plantilla.cos_html = request.POST.get('cos_html', plantilla.cos_html)
            plantilla.activa = bool(request.POST.get('activa'))
            plantilla.save()
            messages.success(request, _('Plantilla actualitzada correctament.'))
            return redirect('portal:plantilles_list')

    class ImportarProspectsView(PortalLoginMixin, View):
        def post(self, request):
            try:
                from modules.marketing.marketing.tasks import importar_prospects_licitacions
                importar_prospects_licitacions.delay()
                messages.success(request, _('Importació de prospects llançada. Els resultats apareixeran en uns moments.'))
            except Exception as e:
                messages.error(request, str(e))
            return redirect('portal:prospects_list')

    class DescubrirProspectsView(PortalLoginMixin, View):
        """AI-assisted prospect discovery: user specifies criteria → system finds matching companies → AI study → approve email."""
        template_name = 'portal/marketing/descobrir.html'

        def get(self, request):
            profile = get_profile(request.user)
            plantilles = PlantillaEmail.objects.filter(activa=True)
            return render(request, self.template_name, {
                'profile': profile,
                'plantilles': plantilles,
                'sectors': EmpresaProspect.Sector.choices,
            })

        def post(self, request):
            profile = get_profile(request.user)
            action = request.POST.get('action', 'cercar')
            plantilles = PlantillaEmail.objects.filter(activa=True)

            if action == 'cercar':
                ubicacio = request.POST.get('ubicacio', '').strip()
                sector_filtre = request.POST.get('sector', '')
                paraules_clau = request.POST.get('paraules_clau', '').strip()

                resultats = self._cercar_prospects(ubicacio, sector_filtre, paraules_clau)
                analisi_ia = self._analisi_ia(ubicacio, sector_filtre, paraules_clau, resultats)

                return render(request, self.template_name, {
                    'profile': profile,
                    'plantilles': plantilles,
                    'sectors': EmpresaProspect.Sector.choices,
                    'resultats': resultats,
                    'analisi_ia': analisi_ia,
                    'ubicacio': ubicacio,
                    'sector_filtre': sector_filtre,
                    'paraules_clau': paraules_clau,
                })

            elif action == 'afegir_prospects':
                seleccionats_json = request.POST.get('seleccionats', '[]')
                import json
                try:
                    seleccionats = json.loads(seleccionats_json)
                except Exception:
                    seleccionats = []
                creats = 0
                for item in seleccionats:
                    nom = item.get('nom', '').strip()
                    if not nom:
                        continue
                    if not EmpresaProspect.objects.filter(nom__iexact=nom).exists():
                        EmpresaProspect.objects.create(
                            nom=nom,
                            sector=item.get('sector', 'CONSTRUCCIO'),
                            email_principal=item.get('email', ''),
                            web=item.get('web', ''),
                            poblacio=item.get('poblacio', ''),
                            provincia=item.get('provincia', ''),
                            notes=item.get('notes', ''),
                            origen='LICITACIO' if item.get('de_licitacio') else 'MANUAL',
                        )
                        creats += 1
                if creats:
                    messages.success(request, _(f'{creats} prospect(s) afegit(s) correctament.'))
                else:
                    messages.info(request, _('Cap prospect nou afegit (ja existien o cap seleccionat).'))
                return redirect('portal:prospects_list')

            elif action == 'enviar_email':
                prospect_id = request.POST.get('prospect_id')
                plantilla_id = request.POST.get('plantilla_id')
                if prospect_id and plantilla_id:
                    try:
                        prospect = EmpresaProspect.objects.get(pk=prospect_id)
                        plantilla = PlantillaEmail.objects.get(pk=plantilla_id)
                        self._enviar_email_directe(prospect, plantilla, request.user)
                        messages.success(request, _(f'Email enviat a {prospect.nom}.'))
                    except Exception as e:
                        messages.error(request, str(e))
                return redirect('portal:descobrir_prospects')

            return redirect('portal:descobrir_prospects')

        def _cercar_prospects(self, ubicacio, sector, paraules_clau):
            resultats = []
            existing_noms = set(EmpresaProspect.objects.values_list('nom', flat=True))

            if _LICITACIONES:
                from django.db.models import Q
                qs = Licitacion.objects.select_related('organismo').filter(organismo__isnull=False)
                if ubicacio:
                    qs = qs.filter(
                        Q(provincia__icontains=ubicacio) |
                        Q(municipio__icontains=ubicacio)
                    )
                if paraules_clau:
                    qs = qs.filter(
                        Q(titulo__icontains=paraules_clau) |
                        Q(organismo__nombre__icontains=paraules_clau)
                    )
                qs = qs.order_by('-creado_en')[:500]

                vists = set()
                for lit in qs:
                    org = lit.organismo
                    if not org:
                        continue
                    nom = getattr(org, 'nombre', '') or str(org)
                    if nom in vists:
                        continue
                    vists.add(nom)
                    resultats.append({
                        'nom': nom,
                        'sector': sector or 'ADMINISTRACIO',
                        'poblacio': lit.municipio or '',
                        'provincia': lit.provincia or '',
                        'de_licitacio': True,
                        'licitacio_pk': lit.pk,
                        'licitacio_titol': lit.titulo[:80],
                        'licitacio_expediente': lit.expediente_id or '',
                        'licitacio_import': float(lit.importe_base) if lit.importe_base else 0,
                        'licitacio_termini': str(lit.fecha_limite_oferta) if lit.fecha_limite_oferta else '',
                        'import_referencia': float(lit.importe_base) if lit.importe_base else 0,
                        'ja_es_prospect': nom in existing_noms,
                        'email': '',
                        'web': '',
                        'notes': f'Detectat via licitació: {lit.expediente_id}',
                    })
                    if len(resultats) >= 30:
                        break

            return resultats

        def _analisi_ia(self, ubicacio, sector, paraules_clau, resultats):
            if not resultats:
                return ''
            try:
                from modules.licitaciones.extraccion.ollama.client import OllamaClient
                from django.conf import settings as dj_settings
                client = OllamaClient()
                model = getattr(dj_settings, 'OLLAMA_MODEL', 'llama3.2:3b')
                noms = [r['nom'] for r in resultats[:10]]
                context = f"paraules clau: '{paraules_clau}'" if paraules_clau else ''
                prompt = (
                    f"Ets un consultor de màrqueting B2B. Has trobat les següents empreses/organismes "
                    f"a la zona '{ubicacio or 'general'}' del sector '{sector or 'construcció'}' {context}: "
                    f"{', '.join(noms)}. "
                    f"Fes una breu anàlisi (màx 150 paraules) sobre el potencial comercial d'aquestes "
                    f"empreses com a clients/socis i quina estratègia de contacte recomanaries. "
                    f"Respon en català i de forma concisa."
                )
                return client.generate(model=model, prompt=prompt) or ''
            except Exception:
                return ''

        def _enviar_email_directe(self, prospect, plantilla, user):
            from modules.marketing.marketing.models import CampanyaMarketing, EnviamentEmail
            from django.core.mail import send_mail
            from django.conf import settings as dj_settings

            cos = plantilla.cos_text
            for var, val in [
                ('{nom_prospect}', prospect.nom),
                ('{persona_contacte}', prospect.persona_contacte or prospect.nom),
                ('{sector}', prospect.get_sector_display()),
                ('{poblacio}', prospect.poblacio or ''),
                ('{empresa_nom}', dj_settings.DEFAULT_FROM_EMAIL),
                ('{web}', prospect.web or ''),
            ]:
                cos = cos.replace(var, val)

            assumpte = plantilla.assumpte
            for var, val in [
                ('{nom_prospect}', prospect.nom),
                ('{empresa_nom}', dj_settings.DEFAULT_FROM_EMAIL),
            ]:
                assumpte = assumpte.replace(var, val)

            send_mail(
                subject=assumpte,
                message=cos,
                from_email=dj_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[prospect.email_principal],
                fail_silently=False,
            )

            campanya, _ = CampanyaMarketing.objects.get_or_create(
                nom=f'Enviament directe — {plantilla.nom}',
                defaults={'plantilla': plantilla, 'creada_per': user, 'estat': 'COMPLETADA'},
            )
            EnviamentEmail.objects.create(
                campanya=campanya,
                prospect=prospect,
                assumpte_final=assumpte,
                cos_final_text=cos,
                estat='ENVIAT',
            )


# ─── Gestió Documental ────────────────────────────────────────────────────────

if _DOCUMENTS:
    class DocumentListView(PortalLoginMixin, View):
        template_name = 'portal/documents/document_list.html'

        def get(self, request):
            profile = get_profile(request.user)
            qs = Document.objects.select_related('categoria', 'pujat_per').order_by('-creada_en')
            q = request.GET.get('q', '').strip()
            categoria = request.GET.get('categoria', '')
            tipus = request.GET.get('tipus', '')
            estat = request.GET.get('estat', '')
            if q:
                qs = qs.filter(nom__icontains=q)
            if categoria:
                qs = qs.filter(categoria__codi=categoria)
            if tipus:
                qs = qs.filter(tipus=tipus)
            if estat:
                qs = qs.filter(estat=estat)
            categories = CategoriaDocument.objects.order_by('nom')
            return render(request, self.template_name, {
                'documents': qs,
                'categories': categories,
                'tipus_choices': Document.Tipus.choices,
                'estat_choices': Document.Estat.choices,
                'filtres': {'q': q, 'categoria': categoria, 'tipus': tipus, 'estat': estat},
                'avui': timezone.now().date(),
                'profile': profile,
            })

    class DocumentDetailView(PortalLoginMixin, View):
        template_name = 'portal/documents/document_detail.html'

        def get(self, request, pk):
            profile = get_profile(request.user)
            document = get_object_or_404(Document.objects.select_related('categoria', 'pujat_per'), pk=pk)
            versions = VersioDocument.objects.filter(document=document).order_by('-numero_versio')
            accessos = AccesDocument.objects.filter(document=document).order_by('-timestamp')[:20]
            download_url = None
            try:
                from modules.documents.documents.services import descarregar_document, verificar_permisos
                if verificar_permisos(document, request.user, 'VISUALITZA'):
                    download_url = descarregar_document(document, request.user, accio='VISUALITZA')
            except Exception:
                pass
            return render(request, self.template_name, {
                'document': document,
                'versions': versions,
                'accessos': accessos,
                'download_url': download_url,
                'profile': profile,
            })

        def post(self, request, pk):
            document = get_object_or_404(Document, pk=pk)
            action = request.POST.get('action', '')
            if action == 'verificar':
                try:
                    from modules.documents.documents.services import verificar_integritat
                    ok = verificar_integritat(document)
                    if ok:
                        messages.success(request, _('Integritat verificada: SHA-256 correcte.'))
                    else:
                        messages.error(request, _('Error d\'integritat: el fitxer ha estat modificat.'))
                except Exception as e:
                    messages.error(request, str(e))
            elif action == 'arxivar':
                document.estat = Document.Estat.ARXIVAT
                document.save(update_fields=['estat'])
                messages.success(request, _('Document arxivat.'))
            return redirect('portal:document_detail', pk=pk)

    class DocumentUploadView(PortalLoginMixin, View):
        template_name = 'portal/documents/document_upload.html'

        def get(self, request):
            profile = get_profile(request.user)
            categories = CategoriaDocument.objects.order_by('nom')
            return render(request, self.template_name, {
                'categories': categories,
                'tipus_choices': Document.Tipus.choices,
                'profile': profile,
            })

        def post(self, request):
            nom = request.POST.get('nom', '').strip()
            categoria_codi = request.POST.get('categoria', '')
            tipus = request.POST.get('tipus', 'ALTRES')
            fitxer = request.FILES.get('fitxer')
            if not nom or not fitxer or not categoria_codi:
                messages.error(request, _('Nom, categoria i fitxer són obligatoris.'))
                return redirect('portal:document_upload')
            try:
                categoria = get_object_or_404(CategoriaDocument, codi=categoria_codi)
                from modules.documents.documents.services import pujar_document
                doc = pujar_document(
                    fitxer=fitxer,
                    nom=nom,
                    categoria=categoria,
                    pujat_per=request.user,
                    tipus=tipus,
                    descripcio=request.POST.get('descripcio', ''),
                )
                log_action('DOCUMENT_PUJAT', user=request.user, object_id=doc.pk,
                           object_repr=doc.nom, request=request)
                messages.success(request, _('Document pujat correctament.'))
                return redirect('portal:document_detail', pk=doc.pk)
            except Exception as e:
                messages.error(request, str(e))
                return redirect('portal:document_upload')


# ─── Sistema RAG ──────────────────────────────────────────────────────────────

if _PROSPEC:
    class ProspeccioIntelView(PortalLoginMixin, View):
        template_name = 'portal/marketing/prospec_intel.html'

        def _sectors(self):
            return EmpresaProspect.Sector.choices if _MARKETING else []

        def get(self, request):
            from django.core.cache import cache
            profile = get_profile(request.user)
            task_id = request.GET.get('task_id', '')

            if task_id:
                from celery.result import AsyncResult
                result = AsyncResult(task_id)
                cached = cache.get(f'prospec_osm_{task_id}')

                if cached:
                    existing_noms = set()
                    if _MARKETING:
                        existing_noms = set(EmpresaProspect.objects.values_list('nom', flat=True))
                    if cached.get('ok'):
                        resultats = [
                            {**r, 'ja_es_prospect': r.get('nom', '').strip() in existing_noms}
                            for r in cached.get('resultats', [])
                        ]
                        return render(request, self.template_name, {
                            'profile': profile, 'sectors': self._sectors(),
                            'resultats': resultats,
                            'ubicacio': cached.get('ubicacio', ''),
                            'sector_filtre': request.GET.get('sector', ''),
                            'paraules_clau': request.GET.get('paraules_clau', ''),
                        })
                    else:
                        messages.error(request, _('Error en la cerca. Torna-ho a intentar.'))
                        return render(request, self.template_name, {
                            'profile': profile, 'sectors': self._sectors(),
                        })

                state = result.state if result else 'UNKNOWN'
                if state in ('PENDING', 'STARTED', 'RETRY'):
                    return render(request, self.template_name, {
                        'profile': profile, 'sectors': self._sectors(),
                        'task_id': task_id,
                        'task_pending': True,
                        'ubicacio': request.GET.get('ubicacio', ''),
                    })
                elif state == 'FAILURE':
                    messages.error(request, _('Error en la cerca. Torna-ho a intentar.'))

            return render(request, self.template_name, {
                'profile': profile, 'sectors': self._sectors(),
            })

        def post(self, request):
            profile = get_profile(request.user)
            ubicacio = request.POST.get('ubicacio', '').strip()
            sector = request.POST.get('sector', '')
            paraules_clau = request.POST.get('paraules_clau', '').strip()
            action = request.POST.get('action', 'cercar')

            if action == 'cercar':
                if not ubicacio:
                    messages.warning(request, _('Introdueix una ubicació per cercar empreses properes.'))
                    return render(request, self.template_name, {
                        'profile': profile, 'sectors': self._sectors(),
                    })
                from modules.prospec.prospec.tasks import cercar_clients_osm_task
                task = cercar_clients_osm_task.delay(ubicacio, sector, paraules_clau, 60)
                from django.urls import reverse
                import urllib.parse
                params = urllib.parse.urlencode({
                    'task_id': task.id, 'ubicacio': ubicacio,
                    'sector': sector, 'paraules_clau': paraules_clau,
                })
                return redirect(f"{reverse('portal:prospec_intel')}?{params}")

            elif action == 'afegir_prospects' and _MARKETING:
                import json
                try:
                    seleccionats = json.loads(request.POST.get('seleccionats', '[]'))
                except Exception:
                    seleccionats = []
                creats = 0
                for item in seleccionats:
                    nom = item.get('nom', '').strip()
                    if not nom:
                        continue
                    if not EmpresaProspect.objects.filter(nom__iexact=nom).exists():
                        EmpresaProspect.objects.create(
                            nom=nom,
                            sector=item.get('sector', 'ALTRES'),
                            email_principal=item.get('email', ''),
                            web=item.get('web', ''),
                            telefon=item.get('telefon', ''),
                            poblacio=item.get('poblacio', ''),
                            provincia=item.get('provincia', ''),
                            notes=item.get('notes', ''),
                            origen='LICITACIO' if item.get('de_licitacio') else 'MANUAL',
                        )
                        creats += 1
                if creats:
                    messages.success(request, _(f'{creats} prospect(s) afegit(s) correctament.'))
                else:
                    messages.info(request, _('Cap prospect nou afegit (ja existien o cap seleccionat).'))
                return redirect('portal:prospects_list')

            return redirect('portal:prospec_intel')


if _ERP:
    class ErpClientListView(PortalLoginMixin, ListView):
        template_name = 'portal/erp/clients.html'
        context_object_name = 'clients'
        paginate_by = 30

        def get_queryset(self):
            qs = ClientERP.objects.filter(actiu=True)
            q = self.request.GET.get('q', '').strip()
            if q:
                qs = qs.filter(Q(nom__icontains=q) | Q(nif__icontains=q) | Q(email__icontains=q))
            return qs

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['profile'] = get_profile(self.request.user)
            return ctx

    class ErpClientCreateView(PortalLoginMixin, View):
        template_name = 'portal/erp/client_form.html'

        def get(self, request):
            return render(request, self.template_name, {'profile': get_profile(request.user), 'action': 'crear'})

        def post(self, request):
            nom = request.POST.get('nom', '').strip()
            if not nom:
                messages.error(request, _('El nom és obligatori.'))
                return render(request, self.template_name, {'profile': get_profile(request.user), 'action': 'crear', 'data': request.POST})
            client = ClientERP.objects.create(
                nom=nom,
                nif=request.POST.get('nif', '').strip(),
                email=request.POST.get('email', '').strip(),
                telefon=request.POST.get('telefon', '').strip(),
                adreca=request.POST.get('adreca', '').strip(),
                poblacio=request.POST.get('poblacio', '').strip(),
                codi_postal=request.POST.get('codi_postal', '').strip(),
                provincia=request.POST.get('provincia', '').strip(),
                pais=request.POST.get('pais', 'España').strip(),
                notes=request.POST.get('notes', '').strip(),
            )
            log_action('ERP_CLIENT_CREATE', user=request.user, request=request, extra={'client_id': client.pk})
            messages.success(request, _('Client creat correctament.'))
            return redirect('portal:erp_clients')

    class ErpFacturesListView(PortalLoginMixin, ListView):
        template_name = 'portal/erp/factures.html'
        context_object_name = 'factures'
        paginate_by = 25

        def get_queryset(self):
            qs = Factura.objects.select_related('client').order_by('-data_emisio', '-numero')
            estat = self.request.GET.get('estat', '')
            q = self.request.GET.get('q', '').strip()
            if estat:
                qs = qs.filter(estat=estat)
            if q:
                qs = qs.filter(Q(numero_complet__icontains=q) | Q(client__nom__icontains=q) | Q(client__nif__icontains=q))
            return qs

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['profile'] = get_profile(self.request.user)
            ctx['estats'] = Factura.Estat.choices
            ctx['filtres'] = self.request.GET
            from django.db.models import Sum
            ctx['total_pendent'] = Factura.objects.filter(
                estat__in=[Factura.Estat.EMESA, Factura.Estat.VENÇUDA]
            ).aggregate(t=Sum('total'))['t'] or 0
            return ctx

    class ErpFacturaDetailView(PortalLoginMixin, View):
        template_name = 'portal/erp/factura_detail.html'

        def get(self, request, pk):
            factura = get_object_or_404(Factura.objects.select_related('client', 'albara', 'pedido'), pk=pk)
            return render(request, self.template_name, {
                'factura': factura,
                'linies': factura.linies.all(),
                'profile': get_profile(request.user),
            })

        def post(self, request, pk):
            factura = get_object_or_404(Factura, pk=pk)
            action = request.POST.get('action', '')
            if action == 'canviar_estat':
                nou_estat = request.POST.get('estat', '')
                if nou_estat in dict(Factura.Estat.choices):
                    factura.estat = nou_estat
                    factura.save(update_fields=['estat', 'actualitzat_en'])
                    messages.success(request, _('Estat actualitzat.'))
            return redirect('portal:erp_factura_detail', pk=pk)

    class ErpFacturaCreateView(PortalLoginMixin, View):
        template_name = 'portal/erp/factura_form.html'

        def get(self, request):
            clients = ClientERP.objects.filter(actiu=True).order_by('nom')
            return render(request, self.template_name, {
                'clients': clients,
                'profile': get_profile(request.user),
                'estats': Factura.Estat.choices,
            })

        def post(self, request):
            client_id = request.POST.get('client_id')
            try:
                client = ClientERP.objects.get(pk=client_id)
            except ClientERP.DoesNotExist:
                messages.error(request, _('Client no vàlid.'))
                return redirect('portal:erp_factura_create')

            from decimal import Decimal as _D, InvalidOperation
            irpf_pct = _D('0')
            try:
                irpf_pct = _D(request.POST.get('irpf_percentatge', '0') or '0')
            except InvalidOperation:
                pass

            factura = Factura(
                client=client,
                data_emisio=request.POST.get('data_emisio') or timezone.now().date(),
                data_venciment=request.POST.get('data_venciment') or None,
                irpf_percentatge=irpf_pct,
                notes=request.POST.get('notes', '').strip(),
                verifactu=request.POST.get('verifactu') == 'on',
                creat_per=request.user,
            )
            factura.save()
            log_action('ERP_FACTURA_CREATE', user=request.user, request=request, extra={'factura_id': factura.pk})
            messages.success(request, _('Factura creada. Ara podeu afegir les línies.'))
            return redirect('portal:erp_factura_detail', pk=factura.pk)

    class ErpAnalitzarDocumentView(PortalLoginMixin, View):
        """
        Two-step workflow:
        Step 1 (GET): show upload form (choose type: factura/albara/pedido)
        Step 2 (POST upload): AI extracts → store in session → redirect back with dades
        Step 2b (POST create): validate pre-filled form → create ERP record
        """
        template_name = 'portal/erp/analitzar_document.html'

        TIPUS_CHOICES = [
            ('factura', _('Factura')),
            ('albara', _('Albarà')),
            ('pedido', _('Pedido')),
        ]

        def get(self, request):
            tipus = request.GET.get('tipus', 'factura')
            dades = request.session.pop('erp_dades_ia', None)
            clients = ClientERP.objects.filter(actiu=True).order_by('nom')
            return render(request, self.template_name, {
                'tipus': tipus,
                'dades': dades,
                'clients': clients,
                'tipus_choices': self.TIPUS_CHOICES,
                'profile': get_profile(request.user),
            })

        def post(self, request):
            action = request.POST.get('action', 'analitzar')
            tipus = request.POST.get('tipus', 'factura')

            if action == 'analitzar':
                fitxer = request.FILES.get('document')
                if not fitxer:
                    messages.error(request, _('Selecciona un fitxer PDF o imatge.'))
                    return redirect(f"{reverse('portal:erp_analitzar')}?tipus={tipus}")

                allowed = ('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp')
                if not any(fitxer.name.lower().endswith(ext) for ext in allowed):
                    messages.error(request, _('Format no admès. Puja un PDF o imatge.'))
                    return redirect(f"{reverse('portal:erp_analitzar')}?tipus={tipus}")

                try:
                    from modules.erp.erp.extraccio import extraure_dades_ia
                    import io
                    contingut = fitxer.read()
                    nom = fitxer.name.lower()

                    if nom.endswith('.pdf'):
                        try:
                            import pypdf
                            reader = pypdf.PdfReader(io.BytesIO(contingut))
                            text = '\n'.join(p.extract_text() or '' for p in reader.pages)[:8000]
                        except Exception:
                            text = ''
                    else:
                        try:
                            from PIL import Image
                            import pytesseract
                            img = Image.open(io.BytesIO(contingut))
                            text = pytesseract.image_to_string(img, lang='spa+cat+eng')[:8000]
                        except Exception:
                            text = ''

                    if not text.strip():
                        messages.warning(request, _('No s\'ha pogut llegir text del document. Introdueix les dades manualment.'))
                        request.session['erp_dades_ia'] = {'tipus': tipus, 'dades': {}, 'fitxer_nom': fitxer.name}
                    else:
                        dades = extraure_dades_ia(text, tipus=tipus)
                        request.session['erp_dades_ia'] = {'tipus': tipus, 'dades': dades, 'fitxer_nom': fitxer.name}
                        messages.success(request, _('Document analitzat. Revisa les dades extretes.'))
                except Exception as exc:
                    logger.error('ERP AI analysis error: %s', exc)
                    messages.warning(request, _('Error en l\'anàlisi. Introdueix les dades manualment.'))
                    request.session['erp_dades_ia'] = {'tipus': tipus, 'dades': {}, 'fitxer_nom': fitxer.name}

                return redirect(f"{reverse('portal:erp_analitzar')}?tipus={tipus}")

            elif action == 'crear_factura':
                client_id = request.POST.get('client_id')
                try:
                    client = ClientERP.objects.get(pk=client_id)
                except ClientERP.DoesNotExist:
                    messages.error(request, _('Client no vàlid.'))
                    return redirect(f"{reverse('portal:erp_analitzar')}?tipus=factura")

                from decimal import Decimal as _D, InvalidOperation
                def dec(val, default='0'):
                    try:
                        return _D(str(val).replace(',', '.') or default)
                    except InvalidOperation:
                        return _D(default)

                factura = Factura(
                    client=client,
                    data_emisio=request.POST.get('data_emisio') or timezone.now().date(),
                    data_venciment=request.POST.get('data_venciment') or None,
                    irpf_percentatge=dec(request.POST.get('irpf_percentatge', '0')),
                    notes=request.POST.get('notes', '').strip(),
                    verifactu=request.POST.get('verifactu') == 'on',
                    creat_per=request.user,
                )
                factura.save()

                from modules.erp.erp.models import LiniaFactura
                descripcio = request.POST.get('linia_descripcio', '').strip()
                if descripcio:
                    LiniaFactura.objects.create(
                        factura=factura,
                        descripcio=descripcio,
                        quantitat=dec(request.POST.get('linia_quantitat', '1'), '1'),
                        preu_unitari=dec(request.POST.get('linia_preu', '0')),
                        iva=dec(request.POST.get('linia_iva', '21')),
                    )
                    factura.recalcular_totals()
                    factura.save()

                log_action('ERP_FACTURA_CREATE', user=request.user, request=request, extra={'pk': factura.pk})
                messages.success(request, _('Factura creada correctament.'))
                return redirect('portal:erp_factura_detail', pk=factura.pk)

            return redirect('portal:erp_analitzar')

    class ErpFacturaDocumentView(PortalLoginMixin, View):
        """Upload a PDF/image to a Factura and extract data with Ollama IA."""

        def post(self, request, pk):
            factura = get_object_or_404(Factura, pk=pk)
            fitxer = request.FILES.get('document')
            if not fitxer:
                messages.error(request, _('Selecciona un fitxer PDF o imatge.'))
                return redirect('portal:erp_factura_detail', pk=pk)

            allowed_ext = ('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp')
            nom = fitxer.name.lower()
            if not any(nom.endswith(ext) for ext in allowed_ext):
                messages.error(request, _('Format no admès. Puja un PDF o imatge.'))
                return redirect('portal:erp_factura_detail', pk=pk)

            factura.document_adjunt = fitxer
            factura.save(update_fields=['document_adjunt', 'actualitzat_en'])

            if request.POST.get('extraure_ia') == 'on':
                try:
                    from modules.erp.erp.extraccio import extraure_text_document, extraure_dades_ia
                    text = extraure_text_document(factura.document_adjunt)
                    if text:
                        dades = extraure_dades_ia(text, tipus='factura')
                        if dades:
                            factura.extraccio_ia = dades
                            factura.save(update_fields=['extraccio_ia', 'actualitzat_en'])
                            messages.success(request, _('Document pujat i dades extretes per IA.'))
                        else:
                            messages.warning(request, _('Document pujat. La IA no ha pogut extreure dades estructurades.'))
                    else:
                        messages.warning(request, _('Document pujat però no s\'ha pogut llegir el text.'))
                except Exception as e:
                    logger.error('ERP IA extraction error: %s', e)
                    messages.warning(request, _('Document pujat. Error en l\'extracció IA.'))
            else:
                messages.success(request, _('Document adjuntat correctament.'))

            return redirect('portal:erp_factura_detail', pk=pk)

    class ErpAlbaransListView(PortalLoginMixin, ListView):
        template_name = 'portal/erp/albarans.html'
        context_object_name = 'albarans'
        paginate_by = 25

        def get_queryset(self):
            qs = Albara.objects.select_related('client').order_by('-data', '-creat_en')
            estat = self.request.GET.get('estat', '')
            q = self.request.GET.get('q', '').strip()
            if estat:
                qs = qs.filter(estat=estat)
            if q:
                qs = qs.filter(Q(numero__icontains=q) | Q(client__nom__icontains=q))
            return qs

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['profile'] = get_profile(self.request.user)
            ctx['estats'] = Albara.Estat.choices
            ctx['filtres'] = self.request.GET
            return ctx

    class ErpPedidosListView(PortalLoginMixin, ListView):
        template_name = 'portal/erp/pedidos.html'
        context_object_name = 'pedidos'
        paginate_by = 25

        def get_queryset(self):
            qs = PedidoERP.objects.select_related('client').order_by('-data', '-creat_en')
            estat = self.request.GET.get('estat', '')
            q = self.request.GET.get('q', '').strip()
            if estat:
                qs = qs.filter(estat=estat)
            if q:
                qs = qs.filter(Q(numero__icontains=q) | Q(client__nom__icontains=q))
            return qs

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ctx['profile'] = get_profile(self.request.user)
            ctx['estats'] = PedidoERP.Estat.choices
            ctx['filtres'] = self.request.GET
            return ctx


if _RAG:
    class RagConsultaView(PortalLoginMixin, View):
        template_name = 'portal/rag/consulta.html'

        def get(self, request):
            profile = get_profile(request.user)
            historial = ConsultaRAG.objects.filter(
                usuari=request.user
            ).order_by('-creada_en')[:20]
            licitacions = []
            if _LICITACIONES:
                licitacions = Licitacion.objects.filter(
                    estado__in=['EN_PREPARACION', 'PRESENTADA', 'ADJUDICADA']
                ).order_by('-creado_en')[:20]
            rag_examples = [
                _('Quantes licitacions tenim en total i quantes són noves?'),
                _('Quants prospects tenim i quants han passat a ser clients?'),
                _('Quin és l\'import total de les factures pendents de cobrament?'),
                _('Quins criteris d\'adjudicació té la licitació X?'),
                _('Llista els documents ISO actius.'),
                _('Quantes ofertes hem guanyat?'),
            ]
            return render(request, self.template_name, {
                'historial': historial,
                'licitacions': licitacions,
                'rag_examples': rag_examples,
                'profile': profile,
            })
