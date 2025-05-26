from django.contrib import admin
from .models import Enfrentamiento, Fase, Usuario, Jugador, Staff, Equipo, Invitacion

# Modelos registrados en Django Admin

@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'legajo', 'riot_id', 'telefono', 'pais')
    search_fields = ('nombre', 'apellido', 'legajo','riot_id')

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'email')
    search_fields = ('nombre', 'apellido', 'email')

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'abreviatura', 'creado_por', 'estadoAprobacion')
    list_filter = ('estadoAprobacion',)
    search_fields = ('nombre', 'creado_por__nombre')

@admin.register(Invitacion)
class InvitacionAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'jugador_invitado', 'aceptada')
    list_filter = ('aceptada',)
    search_fields = ('equipo__nombre', 'jugador_invitado__nombre')

@admin.register(Fase)
class FaseAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden')
    search_fields = ('nombre',)

@admin.register(Enfrentamiento)
class EnfrentamientoAdmin(admin.ModelAdmin):
    list_display = ('fase', 'equipo1', 'equipo2', 'fecha', 'completado', 'ganador')
    list_filter = ('fase', 'completado')
    search_fields = ('equipo1__nombre', 'equipo2__nombre')