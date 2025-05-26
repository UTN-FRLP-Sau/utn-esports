from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('faq/', views.Faq.as_view(), name='faq'),
    path('reglamento/', views.Reglamento.as_view(), name='reglamento'),
    path('sponsors/', views.Sponsors.as_view(), name='sponsors'),
    path('register/', views.RegistroView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Jugador
    path('player/home/', views.PlayerHomeView.as_view(), name='player_home'),
    path('player/perfil/', views.PerfilView.as_view(), name='perfil'),
    path('player/crear_equipo/', views.CrearEquipoView.as_view(), name='crear_equipo'),
    path('player/editar_equipo/<int:equipo_id>/', views.EditarEquipoView.as_view(), name='editar_equipo'),
    path('player/eliminar_equipo/<int:equipo_id>/', views.EliminarEquipoView.as_view(), name='eliminar_equipo'),
    path('player/abandonar_equipo/<int:equipo_id>/', views.AbandonarEquipoView.as_view(), name='abandonar_equipo'),
    path('player/pagar_inscripcion/<int:equipo_id>/', views.PagarInscripcionView.as_view(), name='pagar_inscripcion'),
    path('player/eliminar_jugador/<int:jugador_id>/', views.EliminarJugadorView.as_view(), name='eliminar_jugador'),
    path('player/inscripcion_deshabilitada/', views.InscripcionDeshabilitadaView.as_view(), name='inscripcion_deshabilitada'),
    path('player/ver_competencia/', views.VerCompetenciaView.as_view(), name='ver_competencia'),

    # Invitaciones
    path('player/invitar/<int:equipo_id>/', views.InvitarJugadorView.as_view(), name='invitar_jugador'),
    path('player/invitaciones/<int:invitacion_id>/aceptar/', views.AceptarInvitacionView.as_view(), name='aceptar_invitacion'),
    path('player/invitaciones/<int:invitacion_id>/rechazar/', views.RechazarInvitacionView.as_view(), name='rechazar_invitacion'),

    # Staff
    path('staff/home/', views.StaffHomeView.as_view(), name='staff_home'),
    path('staff/obtener_integrantes/<int:equipo_id>/', views.ObtenerIntegrantesView.as_view(), name='obtener_integrantes'),
    path('staff/cambiar_permiso_edicion_perfil/', views.CambiarPermisoEdicionPerfilView.as_view(), name='cambiar_permiso_edicion_perfil'),
    path('staff/cambiar_estado_inscripciones/', views.CambiarEstadoInscripcionesView.as_view(), name='cambiar_estado_inscripciones'),
    
    path('staff/gestionar_competencia/', views.GestionarCompetenciaView.as_view(), name='gestionar_competencia'),
    path('staff/crear_fase/', views.CrearFaseView.as_view(), name='crear_fase'),
    path('staff/crear_enfrentamiento/', views.CrearEnfrentamientoView.as_view(), name='crear_enfrentamiento'),
    path('staff/asignar_ganador/<int:enfrentamiento_id>/', views.AsignarGanadorView.as_view(), name='asignar_ganador'),
    path('eliminar_fase/<int:pk>/', views.EliminarFaseView.as_view(), name='eliminar_fase'),
    path('eliminar_enfrentamiento/<int:pk>/', views.EliminarEnfrentamientoView.as_view(), name='eliminar_enfrentamiento'),
    
    # Clips Twitch
    path('staff/gestionar_clips/', views.GestionarClipsView.as_view(), name='gestionar_clips'),
    path('staff/cambiar_estado_clip/<int:clip_id>/', views.CambiarEstadoClipView.as_view(), name='cambiar_estado_clip'),
    path('staff/eliminar_clip/<int:clip_id>/', views.EliminarClipView.as_view(), name='eliminar_clip'),
]


# Sirve archivos multimedia en modo de desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)