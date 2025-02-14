from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf.urls.static import static
from django.conf import settings

from .views import (
    InformativeDataView, ObjectPhotoView, AllDataViewSet, ObjectIdAndCoordinatesViewSet,
    InvestorInfoViewSet, AllDataUserViewSet, AllObjectInvestorsViewSet,
    AllDataAllUsersViewSet, CategoryListView, LocationView, ApproveRejectView, InvestorInfoOwnListView,
    AllDataFilterView, AllDataFilterByLatLongDistanceView, AreaListView, SmartNoteCreateView,
    SmartNoteListView, SmartNoteRetrieveView, SmartNoteDestroyView, SmartNoteUpdateView,
    CurrencyListView, CustomAlldataAllUsersListView, FaqRetriveView, CategoryApiListView,
    MainDataAPIView, FinancialDataAPIView, ObjectPhotoViewList, AllDataCatListAPIView,
    CategoryRetrieveView, AreaAPIDeatilView, AreaMainAPIListView, IntroView, PhoneView, UsageProcedureView, OfferView,
    UserCheckingDataViewSet, UserApprovedDataViewSet, UserRejectedDataViewSet, ViewCountAllDataView, TopAllDataView,
    DevicesView, DevicesCreateView, ExchangeRatesView, SearchData,
)

router = DefaultRouter()
router.register('all-data', AllDataViewSet, basename="all-data")
router.register('all-data-user', AllDataUserViewSet, basename="all-data-user")
router.register('all-data-all-users', AllDataAllUsersViewSet, basename="all-data-all-users")

router.register('coordinates', ObjectIdAndCoordinatesViewSet)
router.register('investor-info', InvestorInfoViewSet)
router.register('all-data-investors', AllObjectInvestorsViewSet, basename="all-data-investors")

# 2025-01-22 sanada qoshilgan kodlar
router.register('mydata-checking', UserCheckingDataViewSet, basename="mydata-checking")
router.register('mydata-approved', UserApprovedDataViewSet, basename="mydata-approved")
router.register('mydata-rejected', UserRejectedDataViewSet, basename="mydata-rejected")

urlpatterns = [
    # search
    path('search/', SearchData.as_view()),

    path('main-data-create-api', MainDataAPIView.as_view()),
    path('informative-data-create', InformativeDataView.as_view()),
    path('financial-data-create-api', FinancialDataAPIView.as_view()),
    path('object-photo', ObjectPhotoView.as_view()),
    path('object-photo-get', ObjectPhotoViewList.as_view()),
    # path('set-status-ready', SetReadyStatusView.as_view()),

    # bir xil vazifa
    path('category-list', CategoryListView.as_view()),
    path('category-list-api', CategoryApiListView.as_view()),

    path('category-list-api/<int:pk>/', CategoryRetrieveView.as_view()),
    # tushunmadim
    path('alldata-cat-list-api', AllDataCatListAPIView.as_view()),

    path('currency-list', CurrencyListView.as_view()),
    path('area-list', AreaListView.as_view()),
    # bir xil vazifa
    path('area_main-list-api/', AreaMainAPIListView.as_view()),

    path('area_main-list-api/<int:pk>/', AreaAPIDeatilView.as_view()),

    path('location', LocationView.as_view()),
    path('approve-reject-investor', ApproveRejectView.as_view()),
    path('investor-info-own', InvestorInfoOwnListView.as_view()),
    path('all-data-filter', AllDataFilterView.as_view()),
    path('all-data-by-lat-long-distance-filter', AllDataFilterByLatLongDistanceView.as_view()),

    path('smart-note-delete/<pk>', SmartNoteDestroyView.as_view()),
    path('smart-note-update/<pk>', SmartNoteUpdateView.as_view()),
    path('smart-note-get/<pk>', SmartNoteRetrieveView.as_view()),
    path('smart-note-create', SmartNoteCreateView.as_view()),
    path('smart-note-list', SmartNoteListView.as_view()),
    path('custom-all-data-all-users/<pk>', CustomAlldataAllUsersListView.as_view()),
    path('faqs', FaqRetriveView.as_view()),

    path('phone/', PhoneView.as_view(), name='phone'),
    path('usage-procedure/', UsageProcedureView.as_view(), name='usage-procedure'),
    path('offer/', OfferView.as_view(), name='offer'),
    path('intro/', IntroView.as_view(), name='intro'),

    # 2025-01-22 sanada qoshilgan kodlar
    path('top-all-data', TopAllDataView.as_view()),
    path('view-count-all-data', ViewCountAllDataView.as_view()),
    path('devices', DevicesView.as_view()),
    path('devices-create', DevicesCreateView.as_view()),

    # 2025-02-05 sanada qoshilgan kodlar dollar kursi
    path('exchange-rate/', ExchangeRatesView.as_view(), name='exchange_rate'),

]

urlpatterns += router.urls
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
