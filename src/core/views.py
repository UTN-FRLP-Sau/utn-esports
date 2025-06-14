from datetime import datetime
import json
from django.db import DatabaseError
from django.forms import ValidationError
from django.http import JsonResponse
from django.views.generic import TemplateView, RedirectView, ListView,DetailView 
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from .models import Enfrentamiento, Equipo, EstadoAprobacion, Fase, Invitacion, Jugador, Staff, TwitchClip
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
import filetype
import re
from django.utils.decorators import method_decorator
from .mixins import StaffRequiredMixin

class Home(TemplateView):
    template_name = 'home/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # clips activos de Twitch
        context['twitch_clips'] = TwitchClip.objects.filter(activo=True)
        return context

class Faq(TemplateView):
    template_name = 'faq/faq.html'

class Reglamento(TemplateView):
    template_name = 'reglamento/reglamento.html'

class Sponsors(TemplateView):
    template_name = 'sponsors/sponsors.html'

class InscripcionDeshabilitadaView(TemplateView):
    template_name = 'inscripcion/inscripcion_deshabilitada.html'

# Función para validar el formulario de registro
def validar_formulario(form_data):
    errors = {}

    # Validar contraseñas
    if form_data["password"] != form_data["confirm_password"]:
        errors["password"] = "Las contraseñas no coinciden."

    # Validar longitud de la contraseña
    if len(form_data["password"]) < 8:
        errors["password"] = "La contraseña debe tener al menos 8 caracteres."

    # Validar email único
    if User.objects.filter(email=form_data["email"]).exists():
        errors["email"] = "El correo electrónico ya está registrado."

    # Validar DNI único
    if Jugador.objects.filter(dni=form_data["dni"]).exists():
        errors["dni"] = "El DNI ya está registrado."

    # Validar Riot ID único
    if Jugador.objects.filter(riot_id=form_data["riot_id"]).exists():
        errors["riot_id"] = "El Riot ID ya está registrado."

    # Validar formato de Riot ID
    if form_data["riot_id"] and "#" not in form_data["riot_id"]:
        errors["riot_id"] = "El Riot ID debe contener el símbolo '#'."

    # Validar si se seleccionó una opción en "pertenece-utn"
    if not form_data.get("pertenece_utn"):
        errors["pertenece_utn"] = "Debes seleccionar una opción."

    # Validar legajo único (si pertenece a la UTN)
    if form_data.get("pertenece_utn") == "si":
        if Jugador.objects.filter(legajo=form_data["legajo"]).exists():
            errors["legajo"] = "El legajo ya está registrado."

    # Validar campos obligatorios
    required_fields = ["nombre", "apellido", "dni", "telefono", "telegram", "pais", "riot_id", "email", "password", "confirm_password"]
    if form_data.get("pertenece_utn") == "si":
        required_fields.append("legajo")

    for field in required_fields:
        if not form_data[field]:
            errors[field] = "Este campo es obligatorio."

    # Validar foto (si es necesario)
    if not form_data["foto"]:
        errors["foto"] = "Debes subir una foto."

    # Validar tipo de texto en los campos (solo si el campo no está vacío)
    if form_data["nombre"] and not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+$", form_data["nombre"]):
        errors["nombre"] = "El nombre solo puede contener letras y espacios."

    if form_data["apellido"] and not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+$", form_data["apellido"]):
        errors["apellido"] = "El apellido solo puede contener letras y espacios."

    if form_data["legajo"] and not re.match(r"^\d+$", form_data["legajo"]):
        errors["legajo"] = "El legajo solo puede contener números."

    if form_data["telefono"] and not re.match(r"^[0-9+\-\s]+$", form_data["telefono"]):
        errors["telefono"] = "El teléfono solo puede contener números, espacios, guiones y el símbolo +."

    if form_data["pais"] and re.search(r"\d", form_data["pais"]):
        errors["pais"] = "El país no puede contener números."

    if form_data["email"] and not re.match(r"^[^@]+@[^@]+\.[^@]+$", form_data["email"]):
        errors["email"] = "El correo electrónico no es válido."

    return errors

class RegistroView(View):
    template_name = "register/register.html"
    success_url = reverse_lazy("login")

    def get(self, request, *args, **kwargs):
        # Verifica si las inscripciones están habilitadas
        if not Staff.objects.filter(inscripciones_habilitadas=True).exists():
            messages.error(request, "Las inscripciones están deshabilitadas en este momento.")
            return redirect('inscripcion_deshabilitada')
        else:
            return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # Recuperar los datos del formulario
        form_data = {
            "nombre": request.POST.get("nombre"),
            "apellido": request.POST.get("apellido"),
            "dni": request.POST.get("dni"),
            "telefono": request.POST.get("telefono"),
            "telegram": request.POST.get("telegram"),
            "pais": request.POST.get("pais"),
            "legajo": request.POST.get("legajo"),
            "foto": request.FILES.get("foto"),
            "riot_id": request.POST.get("riot-tag"),
            "email": request.POST.get("email"),
            "password": request.POST.get("password"),
            "confirm_password": request.POST.get("confirm-password"),
            "pertenece_utn": request.POST.get("pertenece-utn"),
        }

        # Validar el formulario
        errors = validar_formulario(form_data)

        # Si hay errores, renderizar el formulario con los errores y los datos ingresados
        if errors:
            return render(request, self.template_name, {"errors": errors, "form_data": form_data})

        # Crear el usuario base (User de Django)
        try:
            user = User.objects.create_user(
                username=form_data["email"],  # Uso el email como nombre de usuario
                email=form_data["email"],
                password=form_data["password"],  # Django aplica el hash automáticamente
            )
        except Exception as e:
            errors["general"] = f"Error al crear el usuario: {e}"
            return render(request, self.template_name, {"errors": errors, "form_data": form_data})

        # Crear el jugador
        try:
            jugador = Jugador.objects.create(
                user=user,
                nombre=form_data["nombre"],
                apellido=form_data["apellido"],
                dni=form_data["dni"],
                foto=form_data["foto"],
                legajo=form_data["legajo"] if form_data["pertenece_utn"] == "si" else None,
                email=form_data["email"],
                telefono=form_data["telefono"],
                telegram=form_data["telegram"],
                pais=form_data["pais"],
                riot_id=form_data["riot_id"],
            )
        except Exception as e:
            user.delete()  # Si algo falla, eliminamos el usuario
            errors["general"] = f"Error al crear el jugador: {e}"
            return render(request, self.template_name, {"errors": errors, "form_data": form_data})

        # Redirigir a la página de inicio
        return redirect(self.success_url)
    
class LoginView(TemplateView):
    template_name = 'login/login.html'

    def get(self, request, *args, **kwargs):
        # Compruebo si hay un parámetro 'next' en la URL, lo que indica que la sesión ha expirado
        if request.GET.get('next'):
            messages.warning(request, "Tu sesión ha expirado. Por favor, inicia sesión nuevamente.", extra_tags='session_expired')
        return render(request, self.template_name)
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Autentica al usuario
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Inicia sesión
            login(request, user)

            # Verifica si el usuario es staff o jugador
            if hasattr(user, 'staff'):  # Si el usuario es staff
                return redirect('staff_home')
            elif hasattr(user, 'jugador'):  # Si el usuario es jugador
                return redirect('player_home')
            else:
                # Si no es ni staff ni jugador, redirige a una página por defecto
                return redirect('home')
        else:
            # Muestra mensaje de error si las credenciales son incorrectas
            messages.error(request, 'Correo electrónico o contraseña incorrectos.', extra_tags='login_error')
            return render(request, self.template_name)
        
class PlayerHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'player/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtiene el jugador asociado al usuario actual
        try:
            jugador = Jugador.objects.get(user=self.request.user)
            context['jugador'] = jugador  # Pasa los datos del jugador a la plantilla

            # Obtiene el equipo al que pertenece el jugador (si existe)
            equipo = jugador.equipo
            context['equipo'] = equipo  # Pasa el equipo a la plantilla

            # Obtiene las invitaciones pendientes del jugador
            invitaciones = Invitacion.objects.filter(jugador_invitado=jugador, aceptada=False)
            context['invitaciones'] = invitaciones  # Pasa las invitaciones a la plantilla

        except Jugador.DoesNotExist:
            context['jugador'] = None
            context['equipo'] = None
            context['invitaciones'] = []

        return context



def validar_edicion_perfil(form_data, jugador_actual):
    errors = {}

    # Validar email único (excepto para el propio usuario)
    if form_data["email"] != jugador_actual.email and User.objects.filter(email=form_data["email"]).exists():
        errors["email"] = "El correo electrónico ya está registrado."

    # Validar DNI único (excepto para el propio usuario)
    if form_data["dni"] != jugador_actual.dni and Jugador.objects.filter(dni=form_data["dni"]).exists():
        errors["dni"] = "El DNI ya está registrado."

    # Validar Riot ID único (excepto para el propio usuario)
    if form_data["riot_id"] != jugador_actual.riot_id and Jugador.objects.filter(riot_id=form_data["riot_id"]).exists():
        errors["riot_id"] = "El Riot ID ya está registrado."

    # Validar formato de Riot ID
    if form_data["riot_id"] and "#" not in form_data["riot_id"]:
        errors["riot_id"] = "El Riot ID debe contener el símbolo '#'."

    # Validar legajo único (si pertenece a la UTN y el legajo ha cambiado)
    if form_data.get("pertenece_utn") == "si" and form_data["legajo"] != jugador_actual.legajo:
        if Jugador.objects.filter(legajo=form_data["legajo"]).exists():
            errors["legajo"] = "El legajo ya está registrado."

    # Validar campos obligatorios
    required_fields = ["nombre", "apellido", "dni", "telefono", "telegram", "pais", "riot_id", "email"]
    if form_data.get("pertenece_utn") == "si":
        required_fields.append("legajo")

    for field in required_fields:
        if not form_data[field]:
            errors[field] = "Este campo es obligatorio."

    # Validar tipo de texto en los campos (solo si el campo no está vacío)
    if form_data["nombre"] and not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+$", form_data["nombre"]):
        errors["nombre"] = "El nombre solo puede contener letras y espacios."

    if form_data["apellido"] and not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÜüÑñ\s]+$", form_data["apellido"]):
        errors["apellido"] = "El apellido solo puede contener letras y espacios."

    if form_data["legajo"] and not re.match(r"^\d+$", form_data["legajo"]):
        errors["legajo"] = "El legajo solo puede contener números."

    if form_data["telefono"] and not re.match(r"^[0-9+\-\s]+$", form_data["telefono"]):
        errors["telefono"] = "El teléfono solo puede contener números, espacios, guiones y el símbolo +."

    if form_data["pais"] and re.search(r"\d", form_data["pais"]):
        errors["pais"] = "El país no puede contener números."

    if form_data["email"] and not re.match(r"^[^@]+@[^@]+\.[^@]+$", form_data["email"]):
        errors["email"] = "El correo electrónico no es válido."

    return errors

class PerfilView(LoginRequiredMixin, TemplateView):
    template_name = 'player/perfil.html'
    success_url = reverse_lazy("perfil")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtiene el jugador asociado al usuario actual
        try:
            jugador = Jugador.objects.get(user=self.request.user)
            context['jugador'] = jugador  # Pasa los datos del jugador a la plantilla
        except Jugador.DoesNotExist:
            context['jugador'] = None  # Si no existe, pasa None

        return context

    def post(self, request, *args, **kwargs):
        # Obtengo el jugador actual
        jugador = get_object_or_404(Jugador, user=request.user)

        # Verifica si la edición del perfil está habilitada
        if not jugador.edicion_habilitada:
            messages.error(request, "La edición de perfiles está deshabilitada.")
            return redirect(self.success_url)

        # Prepara los datos del formulario
        form_data = {
            "nombre": request.POST.get("nombre", ""),
            "apellido": request.POST.get("apellido", ""),
            "dni": request.POST.get("dni", ""),
            "telefono": request.POST.get("telefono", ""),
            "telegram": request.POST.get("telegram", ""),
            "pais": request.POST.get("pais", ""),
            "legajo": request.POST.get("legajo", ""),
            "riot_id": request.POST.get("riot_id", ""),
            "email": request.POST.get("email", ""),
            "pertenece_utn": request.POST.get("pertenece_utn", ""),
        }

        # Valida el formulario
        errors = validar_edicion_perfil(form_data, jugador)

        # Si hay errores, muestra los mensajes y redirige
        if errors:
            for field, error_message in errors.items():
                messages.error(request, f"{field.capitalize()}: {error_message}")
            return redirect(self.success_url)

        # Actualiza los campos del jugador
        jugador.nombre = form_data["nombre"]
        jugador.apellido = form_data["apellido"]
        jugador.dni = form_data["dni"]
        jugador.telefono = form_data["telefono"]
        jugador.telegram = form_data["telegram"]
        jugador.pais = form_data["pais"]
        jugador.legajo = form_data["legajo"]
        jugador.riot_id = form_data["riot_id"]
        jugador.email = form_data["email"]

        # Manejo la foto de perfil (si se sube una nueva)
        if "foto" in request.FILES:
            jugador.foto = request.FILES["foto"]

        try:
            jugador.save()
            # Actualizo el email del usuario de Django si cambia
            if jugador.email != request.user.email:
                request.user.email = jugador.email
                request.user.save()
            messages.success(request, "Perfil actualizado correctamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar el perfil: {e}")

        return redirect(self.success_url)

class CrearEquipoView(LoginRequiredMixin, TemplateView):
    template_name = 'player/crear_equipo.html'

    def get(self, request, *args, **kwargs):
        # Verifica si el usuario es un jugador
        if not hasattr(request.user, 'jugador'):
            messages.error(request, "Solo los jugadores pueden crear equipos.")
            return redirect('player_home')

        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # Verifica si el usuario es un jugador
        if not hasattr(request.user, 'jugador'):
            messages.error(request, "Solo los jugadores pueden crear equipos.")
            return redirect('player_home')

        # Obtiene los datos del formulario
        nombre = request.POST.get('nombre')
        abreviatura = request.POST.get('abreviatura')
        logo = request.FILES.get('logo')
        estadoAprobacion = EstadoAprobacion.PAGO_PENDIENTE

        # Valida los datos
        if not nombre or not abreviatura or not logo:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, self.template_name, {'nombre': nombre, 'abreviatura': abreviatura})

        # Verifica si el nombre del equipo ya existe en la base de datos
        if Equipo.objects.filter(nombre=nombre).exists():
            messages.error(request, "El nombre del equipo ya está en uso. Elige otro.", extra_tags='error-nombre-equipo')
            return render(request, self.template_name, {'nombre': nombre, 'abreviatura': abreviatura})
        
        # Verifica si la abreviatura del equipo ya existe en la base de datos
        if Equipo.objects.filter(abreviatura=abreviatura).exists():
            messages.error(request, "La abreviatura del equipo ya está en uso. Elige otra.", extra_tags='error-abreviatura-equipo')
            return render(request, self.template_name, {'nombre': nombre, 'abreviatura': abreviatura})

        # Validación del tipo de archivo
        try:
            if 'logo' in request.FILES:
                logo = request.FILES['logo']
                kind = filetype.guess(logo.read(1024))  # Analiza los primeros bytes
                if kind is None or kind.mime not in ['image/jpeg', 'image/png', 'image/jpg']:
                    raise ValidationError("Tipo de archivo no permitido para el logo.")

            # Creo el equipo
            equipo = Equipo(
                nombre=nombre,
                abreviatura=abreviatura,
                logo=logo,
                creado_por=request.user.jugador,
                estadoAprobacion=estadoAprobacion,
                capitan=request.user.jugador
            )
            equipo.save()

            # Asocio el equipo al jugador que lo creó
            jugador = request.user.jugador
            jugador.equipo = equipo
            jugador.save()

            # Mensaje de éxito
            messages.success(request, f"Equipo '{equipo.nombre}' creado exitosamente.")
            return redirect('player_home')

        except ValidationError as e:
            messages.error(request, str(e), extra_tags='error-tipo-archivo')
            return render(request, 'player/crear_equipo.html', {'nombre': nombre, 'abreviatura': abreviatura, 'messages': messages.get_messages(request)})



class EditarEquipoView(LoginRequiredMixin, TemplateView):
    template_name = 'player/editar_equipo.html'

    def get(self, request, equipo_id, *args, **kwargs):
        equipo = get_object_or_404(Equipo, id=equipo_id)
        
        # Verifica si el jugador es miembro del equipo
        if request.user.jugador not in equipo.miembros.all():
            messages.error(request, "No tienes permisos para editar este equipo.")
            return redirect('player_home')

        return render(request, self.template_name, {'equipo': equipo})

    def post(self, request, equipo_id, *args, **kwargs):
        equipo = get_object_or_404(Equipo, id=equipo_id)

        # Verifica si el jugador es miembro del equipo
        if request.user.jugador not in equipo.miembros.all():
            messages.error(request, "No tienes permisos para editar este equipo.")
            return redirect('player_home')

        nombre = request.POST.get('nombre')
        abreviatura = request.POST.get('abreviatura')
        logo = request.FILES.get('logo')

        # Verifica si el nombre ha cambiado
        if nombre and nombre != equipo.nombre:
            if Equipo.objects.filter(nombre=nombre).exists():
                messages.error(request, "El nombre del equipo ya está en uso. Elige otro.", extra_tags='error-nombre-equipo')
                return render(request, self.template_name, {'equipo': equipo})

        # Verifica si la abreviatura ha cambiado
        if abreviatura and abreviatura != equipo.abreviatura:
            if Equipo.objects.filter(abreviatura=abreviatura).exists():
                messages.error(request, "La abreviatura del equipo ya está en uso. Elige otra.", extra_tags='error-abreviatura-equipo')
                return render(request, self.template_name, {'equipo': equipo})

        # Actualiza solo los campos que han cambiado
        if nombre and nombre != equipo.nombre:
            equipo.nombre = nombre

        if abreviatura and abreviatura != equipo.abreviatura:
            equipo.abreviatura = abreviatura

        # Valida y actualiza el logo si se ha enviado
        if logo:
            try:
                kind = filetype.guess(logo.read(1024))  # Analiza los primeros bytes
                if kind is None or kind.mime not in ['image/jpeg', 'image/png', 'image/jpg']:
                    raise ValidationError("Tipo de archivo no permitido.")
                logo.seek(0)
                equipo.logo = logo
            except ValidationError as e:
                messages.error(request, str(e), extra_tags='error-tipo-archivo')
                return render(request, self.template_name, {'equipo': equipo})

        # Guarda los cambios
        equipo.save()
        messages.success(request, f"Equipo '{equipo.nombre}' actualizado exitosamente.")
        return redirect('player_home')
    
class EliminarEquipoView(LoginRequiredMixin, View):
    def post(self, request, equipo_id, *args, **kwargs):
        equipo = get_object_or_404(Equipo, id=equipo_id)
        # Verifica si el usuario es el capitán del equipo
        if equipo.capitan == request.user.jugador:
            equipo.delete()
            messages.success(request, f"Equipo '{equipo.nombre}' eliminado exitosamente.")
        else:
            messages.error(request, "Solo el capitán puede eliminar este equipo.")
        return redirect('player_home')


class AbandonarEquipoView(LoginRequiredMixin, View):
    def post(self, request, equipo_id, *args, **kwargs):
        equipo = get_object_or_404(Equipo, id=equipo_id)
        jugador = request.user.jugador

        # Verifica si el jugador es miembro del equipo
        if jugador in equipo.miembros.all():

            # Si el jugador es el capitán, transfiero la capitanía
            if equipo.capitan == jugador:

                # Obtengor otro miembro para transfiero la capitanía
                nuevo_capitan = equipo.miembros.exclude(id=jugador.id).first()  # Excluyo al jugador actual

                if nuevo_capitan:
                    # Transfiero la capitanía al nuevo miembro
                    equipo.capitan = nuevo_capitan
                    equipo.save()
                    messages.success(request, f"La capitanía ha sido transferida a {nuevo_capitan.nombre}.")
                else:
                    equipo.capitan = None

            # Remuevo al jugador del equipo
            equipo.miembros.remove(jugador)

            # Verifica si el equipo quedó sin miembros
            if equipo.miembros.count() == 0:
                equipo.delete()  # Elimino el equipo si no hay más miembros
                messages.success(request, f"Has abandonado el equipo '{equipo.nombre}'. Como eras el último miembro, el equipo ha sido eliminado.")
            else:
                messages.success(request, f"Has abandonado el equipo '{equipo.nombre}' exitosamente.")

            return redirect('player_home')
        else:
            messages.error(request, "Error. No eres miembro de este equipo.")
            return redirect('player_home')

class PagarInscripcionView(LoginRequiredMixin, TemplateView):
    template_name = 'player/pagar_inscripcion.html'

    def get(self, request, *args, **kwargs):
        # Verifica si el usuario es un jugador
        if not hasattr(request.user, 'jugador'):
            messages.error(request, "Solo los jugadores pueden realizar pagos.")
            return redirect('player_home')

        # Verifica si el equipo existe y si el jugador pertenece a ese equipo
        equipo_id = self.kwargs.get('equipo_id')
        try:
            equipo = Equipo.objects.get(id=equipo_id)
            if equipo.creado_por != request.user.jugador and equipo.miembros.filter(id=request.user.jugador.id).count() == 0:
                messages.error(request, "Solo los miembros de este equipo pueden realizar pagos.")
                return redirect('player_home')
        except Equipo.DoesNotExist:
            messages.error(request, "No se encontró el equipo.")
            return redirect('player_home')

        return render(request, self.template_name, {'equipo': equipo})

    def post(self, request, *args, **kwargs):
        # Verifica si el usuario es un jugador
        if not hasattr(request.user, 'jugador'):
            messages.error(request, "Solo los jugadores pueden realizar pagos.")
            return redirect('player_home')

        # Obtiene el ID del equipo
        equipo_id = self.kwargs.get('equipo_id')
        try:
            equipo = Equipo.objects.get(id=equipo_id)
            if equipo.creado_por != request.user.jugador and equipo.miembros.filter(id=request.user.jugador.id).count() == 0:
                messages.error(request, "Solo los miembros de este equipo pueden realizar pagos.")
                return redirect('player_home')
        except Equipo.DoesNotExist:
            messages.error(request, "No se encontró el equipo.")
            return redirect('player_home')

        # Obtiene el archivo de comprobante de pago (único archivo)
        comprobante_pago = request.FILES.get('comprobante_pago')

        if not comprobante_pago:
            messages.error(request, "Debes adjuntar un comprobante de pago.")
            return render(request, self.template_name, {'equipo': equipo})

        # Validación del tipo de archivo
        try:
            kind = filetype.guess(comprobante_pago.read(1024))  # Analiza los primeros bytes
            if kind is None or kind.mime not in ['image/jpeg', 'image/jpg', 'image/png', 'application/zip', 'application/x-rar-compressed']:
                raise ValidationError("Tipo de archivo no permitido para el comprobante de pago.")
            
            # Guarda el comprobante de pago
            equipo.comprobante_pago = comprobante_pago
            equipo.estadoAprobacion = EstadoAprobacion.EN_REVISION
            equipo.save()

            # Mensaje de éxito
            messages.success(request, "Comprobante de pago subido exitosamente. Tu equipo está en revisión.")
            return redirect('player_home')

        except ValidationError as e:
            messages.error(request, str(e), extra_tags='error-tipo-archivo')
            return render(request, self.template_name, {'equipo': equipo, 'messages': messages.get_messages(request)})
class InvitarJugadorView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
        except json.JSONDecodeError:
            return JsonResponse({'error': "Formato de datos inválido."}, status=400)

        equipo_id = self.kwargs.get('equipo_id')
        equipo = get_object_or_404(Equipo, id=equipo_id)

        try:
            jugador_invitado = Jugador.objects.get(email=email)
        except Jugador.DoesNotExist:
            return JsonResponse({'error': "No se encontró un jugador con ese correo electrónico."}, status=400)

        # Validacion para evitar autoinvitaciones
        if request.user.jugador == jugador_invitado:
            return JsonResponse({'error': "No puedes invitarte a ti mismo."}, status=400)

        if Invitacion.objects.filter(equipo=equipo, jugador_invitado=jugador_invitado, aceptada=False).exists():
            return JsonResponse({'warning': "El jugador ya ha recibido una invitación para este equipo."}, status=200)

        Invitacion.objects.create(equipo=equipo, jugador_invitado=jugador_invitado, aceptada=False)
        return JsonResponse({'success': f"Invitación enviada a {jugador_invitado.nombre} {jugador_invitado.apellido}."}, status=200)
    
class ListarInvitacionesView(LoginRequiredMixin, ListView):
    template_name = 'player_home.html'
    context_object_name = 'invitaciones'

    def get_queryset(self):
        # Obtiene las invitaciones del jugador actual
        return Invitacion.objects.filter(jugador_invitado=self.request.user.jugador, aceptada=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['equipo'] = self.request.user.jugador.equipos_creados.first()
        return context

class AceptarInvitacionView(LoginRequiredMixin,View):
    def post(self, request, *args, **kwargs):
        invitacion_id = self.kwargs.get('invitacion_id')
        invitacion = get_object_or_404(Invitacion, id=invitacion_id)

        # Verifica que la invitación no haya sido aceptada previamente
        if invitacion.aceptada:
            messages.warning(request, "Esta invitación ya ha sido aceptada.", extra_tags='invitacion')
            return redirect('player_home')

        # Verifica que el jugador no esté ya en un equipo
        if invitacion.jugador_invitado.equipo:
            messages.warning(request, "Ya perteneces a un equipo.", extra_tags='invitacion')
            return redirect('player_home')

        # Acepta la invitación
        invitacion.aceptada = True
        invitacion.save()

        # Asigna el equipo al jugador
        invitacion.jugador_invitado.equipo = invitacion.equipo
        invitacion.jugador_invitado.save()

        messages.success(request, f"Has aceptado la invitación para unirte a {invitacion.equipo.nombre}.")
        return redirect('player_home')
    
class RechazarInvitacionView(LoginRequiredMixin,View):
    def post(self, request, *args, **kwargs):
        invitacion_id = self.kwargs.get('invitacion_id')
        invitacion = get_object_or_404(Invitacion, id=invitacion_id)

        # Verifica que la invitación no haya sido aceptada previamente
        if invitacion.aceptada:
            messages.warning(request, "Esta invitación ya ha sido aceptada.")
            return redirect('player_home')

        invitacion.delete()

        messages.success(request, "Has rechazado la invitación.")
        return redirect('player_home')
    


class EliminarJugadorView(LoginRequiredMixin,View):
    def post(self, request, jugador_id):
        # Obtengo el jugador y el equipo actual
        jugador = get_object_or_404(Jugador, id=jugador_id)
        equipo = request.user.jugador.equipo

        # Verifico que el jugador pertenezca al equipo y que sea el capitán
        if jugador in equipo.miembros.all() and request.user.jugador == equipo.capitan:
            # Elimino al jugador del equipo
            equipo.miembros.remove(jugador)
            messages.success(request, f'{jugador.nombre} ha sido eliminado del equipo.')
        else:
            messages.error(request, 'No tienes permiso para eliminar a este jugador.')

        return redirect('player_home') 
    


class StaffHomeView(LoginRequiredMixin, ListView):
    model = Equipo
    template_name = 'staff/home.html'
    context_object_name = 'equipos'
    paginate_by = 10  # Paginación para mostrar 10 equipos por página

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        estado_filter = self.request.GET.get('estado', '')

        if search_query:
            queryset = queryset.filter(nombre__icontains=search_query)
        if estado_filter:
            queryset = queryset.filter(estadoAprobacion=estado_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if Jugador.objects.exists():
            context['edicion_habilitada'] = Jugador.objects.first().edicion_habilitada
        else:
            context['edicion_habilitada'] = False  # Valor por defecto si no hay jugadores
        
        return context

    def post(self, request, *args, **kwargs):
        equipo_id = request.POST.get('equipo_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        equipo = get_object_or_404(Equipo, id=equipo_id)

        # Guarda el estado original
        equipo._original_estadoAprobacion = equipo.estadoAprobacion

        equipo.estadoAprobacion = nuevo_estado
        equipo.save()

        return JsonResponse({'status': 'success', 'nuevo_estado': nuevo_estado})
    
class ObtenerIntegrantesView(LoginRequiredMixin, DetailView):
    model = Equipo
    pk_url_kwarg = 'equipo_id'  # Nombre del parámetro en la URL

    def get(self, request, *args, **kwargs):
        equipo = self.get_object()  # Obtiene el equipo basado en el ID
        integrantes = equipo.miembros.all()
        data = [
            {
                "nombre": f"{jugador.nombre} {jugador.apellido}",
                "esCapitan": jugador == equipo.capitan,
                "riot_id": jugador.riot_id,
                "email": jugador.email,
                "telegram": jugador.telegram
            }
            for jugador in integrantes
        ]
        return JsonResponse(data, safe=False)



class GestionarClipsView(LoginRequiredMixin, View):
    def get(self, request):
        clips = TwitchClip.objects.all()  # Obtener todos los clips
        return render(request, 'staff/gestionar_clips.html', {'clips': clips})

    def post(self, request):
        nombre = request.POST.get('nombre')
        url = request.POST.get('url')
        activo = request.POST.get('activo') == 'on'  # Checkbox devuelve 'on' si está marcado

        # Crear un nuevo clip
        TwitchClip.objects.create(nombre=nombre, url=url, activo=activo)
        messages.success(request, 'Clip guardado correctamente.')
        return redirect('gestionar_clips')

class CambiarEstadoClipView(LoginRequiredMixin, View):
    def post(self, request, clip_id):
        clip = get_object_or_404(TwitchClip, id=clip_id)
        clip.activo = not clip.activo  # Cambiar el estado (activo/inactivo)
        clip.save()
        messages.success(request, f'Clip {"activado" if clip.activo else "desactivado"} correctamente.')
        return redirect('gestionar_clips')

class EliminarClipView(LoginRequiredMixin, View):
    def post(self, request, clip_id):
        clip = get_object_or_404(TwitchClip, id=clip_id)
        clip.delete()  # Eliminar el clip de la base de datos
        messages.success(request, 'Clip eliminado correctamente.')
        return redirect('gestionar_clips')
    

class CambiarPermisoEdicionPerfilView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # Verifica si hay jugadores en la base de datos
            if not Jugador.objects.exists():
                messages.error(request, "No hay jugadores registrados.")
                return redirect('staff_home')

            # Obtén el estado actual del primer jugador
            estado_actual = Jugador.objects.first().edicion_habilitada

            # Cambia el estado de edicion_habilitada para todos los jugadores
            Jugador.objects.update(edicion_habilitada=not estado_actual)
            
            # Mensaje de retroalimentación
            if estado_actual:
                messages.success(request, "La edición de perfiles ha sido deshabilitada para todos los jugadores.")
            else:
                messages.success(request, "La edición de perfiles ha sido habilitada para todos los jugadores.")
        
        except DatabaseError as e:
            messages.error(request, f"Error de base de datos: {e}")
        
        return redirect('staff_home')  # Redirige a la vista del staff
    

class CambiarEstadoInscripcionesView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:

            staff = request.user.staff

            staff.inscripciones_habilitadas = not staff.inscripciones_habilitadas
            staff.save()

            if staff.inscripciones_habilitadas:
                messages.success(request, "Las inscripciones han sido habilitadas.")
            else:
                messages.success(request, "Las inscripciones han sido deshabilitadas.")
        
        except Exception as e:
            messages.error(request, f"Error: {e}")
        
        return redirect('staff_home')
    
class VerCompetenciaView(TemplateView):
    template_name = 'player/ver_competencia.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        jugador = None # Inicializa jugador como None
        
        # Verifica si el usuario está autenticado antes de intentar acceder a 'jugador'
        if self.request.user.is_authenticated:
            try:
                # Intenta obtener el objeto Jugador asociado al usuario
                jugador = self.request.user.jugador
            except Jugador.DoesNotExist:
                # Si el usuario está autenticado pero no tiene un objeto Jugador,
                # 'jugador' seguirá siendo None
                pass 

        fases = Fase.objects.order_by('orden')

        lista_fases_y_enfrentamientos = [
            {
                'fase': fase,
                'enfrentamientos': Enfrentamiento.objects.filter(fase=fase).select_related('equipo1', 'equipo2', 'ganador')
            }
            for fase in fases
        ]

        context['jugador'] = jugador
        context['fases_y_enfrentamientos'] = lista_fases_y_enfrentamientos

        return context


class GestionarCompetenciaView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'staff/gestionar_competencia.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fases'] = Fase.objects.order_by('orden')
        context['equipos'] = Equipo.objects.all()
        return context

class CrearFaseView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request):
        nombre = request.POST.get("nombre")
        orden = request.POST.get("orden")
        Fase.objects.create(nombre=nombre, orden=orden)
        return redirect('gestionar_competencia')

class CrearEnfrentamientoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request):
        fase_id = request.POST.get("fase")
        equipo1_id = request.POST.get("equipo1")
        equipo2_id = request.POST.get("equipo2")
        fecha_str = request.POST.get('fecha')

        fase = Fase.objects.get(pk=fase_id)
        equipo1 = Equipo.objects.get(pk=equipo1_id)
        equipo2 = Equipo.objects.get(pk=equipo2_id)
        fecha = datetime.fromisoformat(fecha_str) if fecha_str else None

        Enfrentamiento.objects.create(fase=fase, equipo1=equipo1, equipo2=equipo2, fecha=fecha)
        
        return redirect('gestionar_competencia')

'''class AsignarGanadorView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, enfrentamiento_id):
        ganador_id = request.POST.get("ganador")
        enfrentamiento = Enfrentamiento.objects.get(pk=enfrentamiento_id)
        enfrentamiento.ganador_id = ganador_id
        enfrentamiento.completado = True
        enfrentamiento.save()
        id_ancla = request.POST.get('volver_a', '')
        url = reverse('gestionar_competencia')
        if id_ancla:
            url += f"#{id_ancla}"
        return redirect(url)'''


class EliminarFaseView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, pk):
        fase = get_object_or_404(Fase, pk=pk)
        fase.delete()
        return redirect('gestionar_competencia')

class EliminarEnfrentamientoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, pk):
        enfrentamiento = get_object_or_404(Enfrentamiento, pk=pk)
        enfrentamiento.delete()
        return redirect('gestionar_competencia')
    

class ActualizarResultadoEnfrentamientoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, pk):
        enfrentamiento = get_object_or_404(Enfrentamiento, pk=pk)
        
        try:
            # Los datos vienen como JSON en el body de la petición AJAX
            data = json.loads(request.body)
            score_equipo1_str = data.get("score_equipo1")
            score_equipo2_str = data.get("score_equipo2")

            # Convierte scores a enteros. Si están vacíos, None.
            score_equipo1 = int(score_equipo1_str) if score_equipo1_str else None
            score_equipo2 = int(score_equipo2_str) if score_equipo2_str else None

            enfrentamiento.score_equipo1 = score_equipo1
            enfrentamiento.score_equipo2 = score_equipo2

            response_data = {
                'success': True,
                'score_equipo1': score_equipo1,
                'score_equipo2': score_equipo2,
                'completado': False,
                'ganador_nombre': None,
                'ganador_id': None,
                'message': 'Resultado guardado.'
            }

            # Lógica para determinar el ganador automáticamente si los scores están presentes
            if score_equipo1 is not None and score_equipo2 is not None:
                enfrentamiento.completado = True
                if score_equipo1 > score_equipo2:
                    enfrentamiento.ganador = enfrentamiento.equipo1
                    response_data['ganador_nombre'] = enfrentamiento.equipo1.nombre
                    response_data['ganador_id'] = enfrentamiento.equipo1.id
                elif score_equipo2 > score_equipo1:
                    enfrentamiento.ganador = enfrentamiento.equipo2
                    response_data['ganador_nombre'] = enfrentamiento.equipo2.nombre
                    response_data['ganador_id'] = enfrentamiento.equipo2.id
                else: # Empate
                    enfrentamiento.ganador = None 
                    response_data['ganador_nombre'] = "Empate"
                    response_data['ganador_id'] = None
                response_data['completado'] = True
            else:
                # Si los scores no están completos, el partido no está completado y no hay ganador definido por score
                enfrentamiento.completado = False
                enfrentamiento.ganador = None
                response_data['message'] = 'Scores incompletos, partido pendiente.'

            enfrentamiento.save()
            return JsonResponse(response_data)

        except (ValueError, json.JSONDecodeError) as e:
            # Maneja el caso donde los scores no son números válidos o el JSON es incorrecto
            print(f"Error en datos de entrada: {e}")
            return JsonResponse({'success': False, 'error': 'Datos de score inválidos.'}, status=400)
        except Exception as e:
            print(f"Error inesperado al actualizar resultado: {e}")
            return JsonResponse({'success': False, 'error': 'Ocurrió un error en el servidor.'}, status=500)