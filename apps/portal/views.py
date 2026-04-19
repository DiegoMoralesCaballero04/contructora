import datetime
from django.conf import settings as django_settings
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum, Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
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


# ─── Auth ────────────────────────────────────────────────────────────────────

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


# ─── Dashboard ───────────────────────────────────────────────────────────────

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


# ─── Licitacions ─────────────────────────────────────────────────────────────

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
            return render(request, self.template_name, {
                'roles': UserProfile.Role.choices,
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
                return render(request, self.template_name, {
                    'roles': UserProfile.Role.choices,
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
            profile.save()

            log_action('CREATE', model_name='User', object_id=str(user.pk),
                       object_repr=username, request=request)
            messages.success(request, f'Usuari "{username}" creat correctament.')
            return redirect('portal:admin_users')

    class UserEditView(AdminAccessMixin, View):
        template_name = 'portal/admin/user_form.html'

        def get(self, request, pk):
            user = get_object_or_404(User, pk=pk)
            profile = get_profile(user)
            return render(request, self.template_name, {
                'edit_user': user,
                'edit_profile': profile,
                'roles': UserProfile.Role.choices,
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
            profile.save()

            nova_pass = request.POST.get('password', '').strip()
            if nova_pass:
                user.set_password(nova_pass)
                user.save()

            log_action('UPDATE', model_name='User', object_id=str(user.pk),
                       object_repr=user.username, request=request)
            messages.success(request, f'Usuari "{user.username}" actualitzat.')
            return redirect('portal:admin_users')

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
