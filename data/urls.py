from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf.urls.static import static
from django.conf import settings

from .views import (
    MainDataView, InformativeDataView, FinancialDataView, ObjectPhotoView,
    MainDataDraftRetrieveView, InformativeDataDraftRetrieveView, FinancialDataDraftRetrieveView,
    # MainDataApprovedRetrieveView, InformativeDataApprovedRetrieveView, FinancialDataApprovedRetrieveView,
    MainDataDraftView, InformativeDataDraftView, FinancialDataDraftView, AllDataViewSet, ObjectIdAndCoordinatesViewSet,
    InvestorInfoView, InvestorInfoViewSet, AllDataUserViewSet, AllObjectInvestorsViewSet,
    AllDataAllUsersViewSet, CategoryListView, LocationView, ApproveRejectView, InvestorInfoOwnListView,
    AllDataFilterView, AllDataFilterByLatLongDistanceView, AreaListView, SmartNoteCreateView,
    SmartNoteListView, SmartNoteRetrieveView, SmartNoteDestroyView, SmartNoteUpdateView,
    CurrencyListView, CustomAlldataAllUsersListView, FaqRetriveView, AreaAPIListView, CategoryApiListView,
    MainDataAPIView, MainDataDraftListView, FinancialDataAPIView, ObjectPhotoViewList, AllDataCatListAPIView,
    CategoryRetrieveView, AreaAPIDeatilView, AreaMainAPIListView
)

router = DefaultRouter()
router.register('all-data', AllDataViewSet)
router.register('all-data-user', AllDataUserViewSet)
router.register('all-data-all-users', AllDataAllUsersViewSet)
router.register('coordinates', ObjectIdAndCoordinatesViewSet)
router.register('investor-info', InvestorInfoViewSet)
router.register('all-data-investors', AllObjectInvestorsViewSet)

urlpatterns = [
    path('main-data-draft-save', MainDataDraftView.as_view()),
    path('main-data-create', MainDataView.as_view()),
    path('main-data-create-api', MainDataAPIView.as_view()),
    path('main-data-draft-get', MainDataDraftRetrieveView.as_view()),
    path('main-data-draft-get-api', MainDataDraftListView.as_view()),
    # path('main-data-approved-get', MainDataApprovedRetrieveView.as_view()),
    path('informative-data-draft-save', InformativeDataDraftView.as_view()),
    path('informative-data-create', InformativeDataView.as_view()),
    path('informative-data-draft-get', InformativeDataDraftRetrieveView.as_view()),
    # path('informative-data-approved-get', InformativeDataApprovedRetrieveView.as_view()),
    path('financial-data-draft-save', FinancialDataDraftView.as_view()),
    # bir xil vazifa
    path('financial-data-create', FinancialDataView.as_view()),
    path('financial-data-create-api', FinancialDataAPIView.as_view()),
    # tushunmadim
    path('financial-data-draft-get', FinancialDataDraftRetrieveView.as_view()),
    # path('financial-data-approved-get', FinancialDataApprovedRetrieveView.as_view()),
    # tushunmadim
    path('object-photo', ObjectPhotoView.as_view()),
    path('object-photo-get', ObjectPhotoViewList.as_view()),
    # path('set-status-ready', SetReadyStatusView.as_view()),

    # kerak bolmasligi mumkin chat qilganligimiz sabbali
    path('investor-info-create', InvestorInfoView.as_view()),
    # bir xil vazifa
    path('category-list', CategoryListView.as_view()),
    path('category-list-api', CategoryApiListView.as_view()),

    path('category-list-api/<int:pk>/', CategoryRetrieveView.as_view()),
    # tushunmadim
    path('alldata-cat-list-api', AllDataCatListAPIView.as_view()),

    path('currency-list', CurrencyListView.as_view()),
    path('area-list', AreaListView.as_view()),
    # bir xil vazifa
    path('area-list-api', AreaAPIListView.as_view()),
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
]

urlpatterns += router.urls
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
