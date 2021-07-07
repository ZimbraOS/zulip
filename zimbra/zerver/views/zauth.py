import logging
import secrets
import urllib
from functools import wraps
from typing import Any, Dict, List, Mapping, Optional, cast
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe
import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseServerError
from zerver.decorator import do_login, log_view_func, process_client, require_post
from zerver.lib.subdomains import get_subdomain, is_subdomain_root_or_alias
from zerver.lib.request import REQ, JsonableError, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.actions import do_add_realm_domain, do_create_realm, do_deactivate_realm, do_change_user_delivery_email
from zerver.views.auth import login_or_register_remote_user
from zerver.lib.users import get_api_key,get_raw_user_data
from zerver.models import UserProfile, get_user_profile_by_email
from zerver.lib.sessions import delete_user_sessions
from zproject.backends import (
    ExternalAuthDataDict,
    ExternalAuthResult,
)
from zerver.models import (
    PreregistrationUser,
    Realm,
    RealmDomain,
    UserProfile,
    filter_to_valid_prereg_users,
    get_realm,
    remote_user_to_email,
)

@csrf_exempt
@log_view_func
def remote_zimbra_jwt(request: HttpRequest) -> HttpResponse:
    subdomain = get_subdomain(request)
    user_profile = getUserProfile(request)
    if user_profile is None:
        result = ExternalAuthResult(data_dict={"email": email, "full_name": remote_user,
                                               "subdomain": realm.subdomain})
    else:
        result = ExternalAuthResult(user_profile=user_profile)
    return login_or_register_remote_user(request, result)

@csrf_exempt
@require_post
@has_request_variables
def zimbra_api_key(request: HttpRequest) -> HttpResponse:
    payload = getPayload(request)
    user_profile = getUserProfile(request)
    api_key = get_api_key(user_profile)
    role = payload.get('role', None)
    updateUserRole(user_profile, role)
    return json_success({"api_key": api_key, "email": user_profile.delivery_email})

@csrf_exempt
@require_post
@has_request_variables
def zimbra_create_realm(request: HttpRequest) -> HttpResponse:
    payload = getPayload(request)
    domain_name = payload.get('domain_name')
    domain_id = payload.get('domain_id')
    try:
        realm = do_create_realm(domain_id, domain_name , emails_restricted_to_domains=False)
        realm_domain = RealmDomain.objects.create(realm=realm, domain=domain_name, allow_subdomains=False)
    except AssertionError as error:
        logging.warn(error)
    return json_success({"domain_id": domain_id})

def updateUserRole(user_profile: UserProfile, role: str):
    if role is not None and user_profile.role != role:
        user_profile.role = role
        user_profile.save()

@csrf_exempt
@require_post
@has_request_variables
def zimbra_deactivate_realm(request: HttpRequest) -> HttpResponse:
    payload = getPayload(request)
    realm_id = payload.get('realm_id')
    try:
        realm = Realm.objects.get(string_id=realm_id)
        realm = do_deactivate_realm(realm)
    except AssertionError as error:
        logging.warn(error)
    return json_success({"realm_id": realm_id})

@csrf_exempt
@require_post
@has_request_variables
def zimbra_allow_domain_realm(request: HttpRequest) -> HttpResponse:
    payload = getPayload(request)
    realm_id = payload.get('realm_id')
    allow_domain_name = payload.get('allow_domain_name')
    old_domain_name = payload.get('old_domain_name')
    allow_subdomain = payload.get('allow_subdomain')
    try:
        realm = Realm.objects.get(string_id=realm_id)
        do_add_realm_domain(realm, allow_domain_name, allow_subdomain)
        user_dict = get_raw_user_data(realm, None, target_user=None, client_gravatar=False, user_avatar_url_field_optional=False, include_custom_profile_fields=False)
        for user_id in user_dict:
            try:
                inner_dict = user_dict[user_id]
                if '@'+old_domain_name in inner_dict["email"]:
                    userProfile = get_user_profile_by_email(inner_dict["email"])
                    if userProfile.is_active:
                        delete_user_sessions(userProfile)
                    do_change_user_delivery_email(userProfile, inner_dict["email"].replace(old_domain_name, allow_domain_name))
            except Exception as exception:
                logging.warn(exception)
    except AssertionError as error:
        logging.warn(error)
    return json_success({"realm_id": realm_id})


def getUserProfile(request: HttpRequest):
    subdomain = get_subdomain(request)
    payload = getPayload(request)
    remote_user = payload.get("user", None)
    if remote_user is None:
        raise JsonableError(_("No user specified in JSON web token claims"))
    email_domain = payload.get('realm', None)
    if email_domain is None:
        raise JsonableError(_("No organization specified in JSON web token claims"))
    email = f"{remote_user}@{email_domain}"

    try:
        realm = get_realm(subdomain)
    except Realm.DoesNotExist:
        raise JsonableError(_("Wrong subdomain"))

    user_profile = authenticate(username=email,
                                realm=realm,
                                use_dummy_backend=True)
    return user_profile

def getPayload(request: HttpRequest):
    subdomain = get_subdomain(request)
    try:
        key = settings.ZIMBRA_JWT_AUTH_KEY
        algorithms = ['HS256']
    except KeyError:
        raise JsonableError(_("Auth key for this subdomain not found."))

    try:
        json_web_token = request.POST["json_web_token"]
        options = {'verify_signature': True}
        payload = jwt.decode(json_web_token, key, algorithms=algorithms, options=options)
    except KeyError:
        raise JsonableError(_("No JSON web token passed in request"))
    except jwt.InvalidTokenError:
        raise JsonableError(_("Bad JSON web token"))
    return payload
