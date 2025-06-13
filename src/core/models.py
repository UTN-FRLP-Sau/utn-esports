from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
import os
from uuid import uuid4


class EstadoAprobacion(models.TextChoices):
    APROBADO = "Aprobado", "Aprobado"
    RECHAZADO = "Rechazado", "Rechazado"
    EN_REVISION = "En revisión", "En revisión"
    PAGO_PENDIENTE = "Pago pendiente", "Pago de inscripción pendiente"

    
class Usuario(models.Model):
    # Roles
    ES_JUGADOR = 'jugador'
    ES_STAFF = 'staff'
    ROL_CHOICES = [
        (ES_JUGADOR, 'Jugador'),
        (ES_STAFF, 'Staff'),
    ]

    # Relación con el modelo User de Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='usuario')

    # Datos comunes para jugadores y staff
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=40, unique=True)
    email = models.EmailField(unique=True)

    # Rol del usuario (jugador o staff)
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default=ES_JUGADOR)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def es_jugador(self):
        return self.rol == self.ES_JUGADOR

    def es_staff(self):
        return self.rol == self.ES_STAFF
    
    # La defino abstracta para que no se cree una tabla en la base de datos
    class Meta:
        abstract = True


def generar_ruta_unica_jugador(instance, filename):
    # Extraer la extensión del archivo
    ext = filename.split('.')[-1]
    # Crear un nombre de archivo único usando UUID
    filename = '{}.{}'.format(uuid4(), ext)
    # Devolver la ruta completa donde se almacenará la imagen
    return os.path.join('fotos', filename)


class Jugador(Usuario):
    # Relacion con el modelo User de Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='jugador')

    # Datos adicionales para jugadores
    telefono = models.CharField(max_length=40)
    telegram = models.CharField(max_length=40)
    pais = models.CharField(max_length=40)
    foto = models.ImageField(upload_to=generar_ruta_unica_jugador, null=True)
    legajo = models.CharField(max_length=40, blank=True ,null=True)

    # Datos de Riot
    riot_id = models.CharField(max_length=40, unique=True)

    # Relación ForeignKey con Equipo
    equipo = models.ForeignKey('Equipo', on_delete=models.SET_NULL, null=True, related_name='miembros', blank=True)

    # Campo para controlar la edición del perfil
    edicion_habilitada = models.BooleanField(default=True)


    
    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Staff(Usuario):
    # Relacion con el modelo User de Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff')
    inscripciones_habilitadas = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


def generar_ruta_unica_logo(instance, filename):
    # Extraer la extensión del archivo
    ext = filename.split('.')[-1]
    # Crear un nombre de archivo único usando UUID
    filename = '{}.{}'.format(uuid4(), ext)
    # Devolver la ruta completa donde se almacenará la imagen
    return os.path.join('logo', filename)


def generar_ruta_unica_comprobante(instance, filename):
    # Extraer la extensión del archivo
    ext = filename.split('.')[-1]
    # Crear un nombre de archivo único usando UUID
    filename = '{}.{}'.format(uuid4(), ext)
    # Devolver la ruta completa donde se almacenará la imagen
    return os.path.join('comprobantes', filename)

class Equipo(models.Model):
    nombre = models.CharField(max_length=40, unique=True)
    abreviatura = models.CharField(max_length=10)
    logo = models.ImageField(upload_to=generar_ruta_unica_logo)
    comprobante_pago = models.ImageField(
        upload_to=generar_ruta_unica_comprobante)
    estadoAprobacion = models.CharField(
        max_length=20,
        choices=EstadoAprobacion.choices,
        default=EstadoAprobacion.PAGO_PENDIENTE
    )
    creado_por = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='equipos_creados')
    capitan = models.ForeignKey(Jugador, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipo_capitan')

    def __str__(self):
        return f"{self.nombre}"


class Invitacion(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='invitaciones')
    jugador_invitado = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='invitaciones_recibidas')
    aceptada = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitación a {self.jugador_invitado} para unirse a {self.equipo}"
    
class TwitchClip(models.Model):
    nombre = models.CharField(max_length=100, help_text="Nombre descriptivo del clip")
    url = models.URLField(help_text="URL completa del clip de Twitch")
    activo = models.BooleanField(default=True, help_text="¿Este clip está activo y debe mostrarse en el carrusel?")

    def __str__(self):
        return self.nombre

    def get_embed_url(self):
        """
        Convierte la URL del clip en un formato compatible con el iframe de Twitch.
        """
        clip_id = self.url.split('/')[-1]  # Extrae el ID del clip de la URL
        return f"https://clips.twitch.tv/embed?clip={clip_id}&parent=127.0.0.1"
    

#####################################################################################################################
################## Sistema de competencia ###########################################################################
#####################################################################################################################


#Define una etapa del torneo (Grupo A, Grupo B, Cuartos de Final, etc.)
class Fase(models.Model):
    NOMBRE_CHOICES = [
        ('GRUPO', 'Fase de Grupos'),
        ('QF', 'Cuartos de Final'),
        ('SF', 'Semifinal'),
        ('FI', 'Final'),
        ('OTRA', 'Otra'),
    ]

    nombre = models.CharField(max_length=20, choices=NOMBRE_CHOICES)
    descripcion = models.TextField(blank=True)
    grupo = models.CharField(max_length=1, blank=True, null=True)  # A, B, C... solo para fase de grupos
    es_eliminatoria = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(help_text="Orden cronológico de la fase")

    @property
    def completada(self):
        return self.enfrentamientos.exists() and all(e.completado for e in self.enfrentamientos.all())
    
    @property
    def no_comenzo(self):
        return not self.enfrentamientos.exists()


    def __str__(self):
        if self.grupo:
            return f"{self.get_nombre_display()} - Grupo {self.grupo}"
        return self.get_nombre_display()


# Representa un partido entre dos equipos (puede ser Bo1 o Bo3).
class Enfrentamiento(models.Model):
    fase = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='enfrentamientos')
    equipo1 = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='enfrentamientos_como_local')
    equipo2 = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='enfrentamientos_como_visitante')
    fecha = models.DateTimeField()
    best_of = models.PositiveIntegerField(default=1)  # 1 para Bo1, 3 para Bo3
    completado = models.BooleanField(default=False)
    ganador = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='enfrentamientos_ganados')

    def __str__(self):
        return f"{self.equipo1} vs {self.equipo2} - {self.fase}"

# Representa una partida individual dentro de un enfrentamiento (sirve para Bo3).
class Partida(models.Model):
    enfrentamiento = models.ForeignKey(Enfrentamiento, on_delete=models.CASCADE, related_name='partidas')
    numero = models.PositiveIntegerField()  # 1, 2, 3...
    equipo_ganador = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='partidas_ganadas')
    duracion = models.DurationField(null=True, blank=True)
    link_replay = models.URLField(blank=True, null=True, help_text="Enlace a la repetición o video")

    def __str__(self):
        return f"Partida {self.numero} - {self.enfrentamiento}"


class ClasificacionGrupo(models.Model):
    equipo = models.ForeignKey('Equipo', on_delete=models.CASCADE)
    grupo = models.CharField(max_length=1)  # A, B, C, etc.
    victorias = models.PositiveIntegerField(default=0)
    derrotas = models.PositiveIntegerField(default=0)
    partidas_jugadas = models.PositiveIntegerField(default=0)
    oro_total = models.PositiveIntegerField(default=0)
    torres_destruidas = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('equipo', 'grupo')

    def __str__(self):
        return f"{self.equipo.nombre} (Grupo {self.grupo})"
    

def actualizar_clasificacion(enfrentamiento):
    fase = enfrentamiento.fase
    if not fase or not fase.grupo:
        return  # solo aplica a fases con grupo (fase de grupos)

    grupo = fase.grupo
    equipo1 = enfrentamiento.equipo1
    equipo2 = enfrentamiento.equipo2
    ganador = enfrentamiento.ganador
    perdedor = equipo1 if equipo2 == ganador else equipo2

    for equipo in [equipo1, equipo2]:
        ClasificacionGrupo.objects.get_or_create(equipo=equipo, grupo=grupo)

    # Actualizar partidas jugadas
    ClasificacionGrupo.objects.filter(equipo=equipo1, grupo=grupo).update(partidas_jugadas=F('partidas_jugadas') + 1)
    ClasificacionGrupo.objects.filter(equipo=equipo2, grupo=grupo).update(partidas_jugadas=F('partidas_jugadas') + 1)

    # Actualizar victorias/derrotas
    ClasificacionGrupo.objects.filter(equipo=ganador, grupo=grupo).update(victorias=F('victorias') + 1)
    ClasificacionGrupo.objects.filter(equipo=perdedor, grupo=grupo).update(derrotas=F('derrotas') + 1)

    # 
    # partidas = enfrentamiento.partidas.all()
    # oro_ganador = sum([getattr(p, 'oro_equipo1' if p.equipo_ganador == equipo1 else 'oro_equipo2', 0) for p in partidas])
    # torres_ganador = sum([getattr(p, 'torres_equipo1' if p.equipo_ganador == equipo1 else 'torres_equipo2', 0) for p in partidas])

    # ClasificacionGrupo.objects.filter(equipo=ganador, grupo=grupo).update(
    #     oro_total=F('oro_total') + oro_ganador,
    #     torres_destruidas=F('torres_destruidas') + torres_ganador
    # )
