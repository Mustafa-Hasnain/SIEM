from django.urls import path
from . import views

urlpatterns = [
    path('create_elasticsearch_index/', views.create_elasticsearch_index, name='create_elasticsearch_index'),
    path('index_data_to_elastic_search/', views.index_data_to_elastic_search, name='index_data_to_elastic_search'),
    path('getIOCS/', views.getIOCS, name='getIOCS'),
    path('index/',views.sample_graph, name="index"),
    path('assets/',views.search_form, name="assets_tab"),
    path('all_logs/',views.all_logs, name="all_logs"),
    path('log_detail/<str:id>/',views.log_detail, name="log_detail"),
    path('search_logs/',views.search_logs, name="search_logs"),
    path('search_logs/<int:page>/',views.search_logs, name="search_logs"),
    path('download_csv/',views.download_csv,name="download_csv"),
    path('search_graphs/',views.search_graphs, name="search_graphs"),
    path('download_pdf/', views.download_pdf, name='download_pdf'),

]