from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

urlpatterns = [
                  path('', views.index, name='index'),
                  path('upload/', views.upload_process_model, name='upload'),
                  path('model/<int:process_model_id>/', views.edit_process_model, name='detail'),
                  path('actor/<int:actor_id>/', views.edit_actor, name='detail_actor'),
                  path('ioaction/<int:iorequest_id>/', views.response_user_interaction, name='user_io_response'),
                  path('enterdata/<int:iorequest_id>/', views.enter_data, name='user_interaction'),
                  path('load/<int:process_model_id>/', views.load_source, name='load_source'),
                  path('recompile/<int:process_model_id>/', views.recompile, name='recompile'),
                  path('start/<int:process_model_id>/', views.start_instance, name='start_instance'),
                  path('manage/', views.manage_running, name='manage_running'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
