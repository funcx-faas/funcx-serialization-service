from models.utils import get_db_connection
from flask import request, current_app as app
import functools

from globus_nexus_client import NexusClient
from globus_sdk import AccessTokenAuthorizer, GlobusAPIError, ConfidentialAppAuthClient

from functools import wraps
from flask import abort


def authenticated(f):
    """Decorator for globus auth."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            abort(401, 'You must be logged in to perform this function.')

        token = request.headers.get('Authorization')
        token = str.replace(str(token), 'Bearer ', '')
        user_name = None
        try:
            client = get_auth_client()
            auth_detail = client.oauth2_token_introspect(token)
            app.logger.debug(auth_detail)
            user_name = auth_detail['username']
        except Exception as e:
            print(e)
            abort(400, "Failed to authenticate user.")
        return f(user_name, *args, **kwargs)
    return decorated_function


def authenticated_w_uuid(f):
    """Decorator for globus auth."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            abort(401, 'You must be logged in to perform this function.')

        token = request.headers.get('Authorization')
        token = str.replace(str(token), 'Bearer ', '')
        user_name = None
        user_uuid = None
        try:
            client = get_auth_client()
            auth_detail = client.oauth2_token_introspect(token)
            app.logger.debug(auth_detail)
            user_name = auth_detail['username']
            user_uuid = auth_detail['sub']
        except Exception as e:
            print(e)
            abort(400, "Failed to authenticate user.")
        return f(user_name, user_uuid, *args, **kwargs)
    return decorated_function


def check_group_membership(token, endpoint_groups):
    """Determine whether or not the user is a member
    of any of the groups

    Parameters
    ----------
    token : str
        The user's nexus token
    endpoint_groups : list
        A list of the group ids associated with the endpoint

    Returns
    -------
    bool
        Whether or not the user is a member of any of the groups
    """
    client = get_auth_client()
    dep_tokens = client.oauth2_get_dependent_tokens(token)

    nexus_token = dep_tokens.by_resource_server['nexus.api.globus.org']["access_token"]

    # Create a nexus client to retrieve the user's groups
    nexus_client = NexusClient()
    nexus_client.authorizer = AccessTokenAuthorizer(nexus_token)
    user_groups = nexus_client.list_groups(my_statuses="active", fields="id", for_all_identities=True)

    # Check if any of the user's groups match
    for user_group in user_groups:
        for endpoint_group in endpoint_groups:
            if user_group['id'] == endpoint_group:
                return True
    return False


@functools.lru_cache()
def authorize_endpoint(user_id, endpoint_uuid, function_uuid, token):
    """Determine whether or not the user is allowed to access this endpoint.
    This is done in two steps: first, check if the user owns the endpoint. If not,
    check if there are any groups associated with the endpoint and determine if the user
    is a member of any of them.

    Parameters
    ----------
    user_id : str
        The primary identity of the user
    endpoint_uuid : str
        The uuid of the endpoint
    function_uuid : str
        The uuid of the function
    token : str
        The auth token

    Returns
    -------
    bool
        Whether or not the user is allowed access to the endpoint
    """

    authorized = False
    try:
        conn, cur = get_db_connection()

        # Check if the user owns the endpoint
        query = "select * from sites where endpoint_uuid = %s"
        cur.execute(query, (endpoint_uuid, ))
        row = cur.fetchone()
        app.logger.debug(f"Endpoint auth row: {row}")

        # If the endpoint is flagged as protected we need to overwrite

        if len(row) > 0:
            # If it is restricted we need to check the function is allowed, otherwise nothing else matters
            if row['restricted']:
                app.logger.debug("Restricted endpoint, checking function is allowed.")
                query = "select * from restricted_endpoint_functions where endpoint_id = %s and function_id = %s"
                cur.execute(query, (endpoint_uuid, function_uuid))
                funcs = cur.fetchall()
                app.logger.debug(f"Length of query response: {len(funcs)}")
                if len(funcs) == 0:
                    # There is no entry of this function, so reject it.
                    raise Exception(f"Function {function_uuid} not permitted on endpoint {endpoint_uuid}")

            # Check if the user owns it
            if row['user_id'] == user_id:
                authorized = True
            # Otherwise if the row is public
            elif row['public']:
                authorized = True

        if not authorized:
            # Check if there are any groups associated with this endpoint
            query = "select * from auth_groups where endpoint_id = %s"
            cur.execute(query, (endpoint_uuid,))
            rows = cur.fetchall()
            endpoint_groups = []
            for row in rows:
                endpoint_groups.append(row['group_id'])
            if len(endpoint_groups) > 0:
                authorized = check_group_membership(token, endpoint_groups)

    except Exception as e:
        print(e)
        app.logger.error(e)
    return authorized



@functools.lru_cache()
def authorize_function(user_id, function_uuid, token):
    """Determine whether or not the user is allowed to access this function.
    This is done in two steps: first, check if the user owns the function. If not,
    check if there are any groups associated with the function and determine if the user
    is a member of any of them.

    Parameters
    ----------
    user_id : str
        The primary identity of the user
    function_uuid : str
        The uuid of the function
    token : str
        The auth token

    Returns
    -------
    bool
        Whether or not the user is allowed access to the function
    """

    authorized = False
    try:
        conn, cur = get_db_connection()

        # Check if the user owns the endpoint
        query = "select * from functions where function_uuid = %s"
        cur.execute(query, (function_uuid, ))
        row = cur.fetchone()
        app.logger.debug(f"Endpoint auth row: {row}")
        if len(row) > 0:
            # Check if the user owns it
            if row['user_id'] == user_id:
                authorized = True
            elif row['public']:
                authorized = True

        if not authorized:
            # Check if there are any groups associated with this function
            query = "select * from function_auth_groups where function_id = %s"
            cur.execute(query, (function_uuid,))
            rows = cur.fetchall()
            endpoint_groups = []
            for row in rows:
                endpoint_groups.append(row['group_id'])
            if len(endpoint_groups) > 0:
                authorized = check_group_membership(token, endpoint_groups)

    except Exception as e:
        print(e)
        app.logger.error(e)
    return authorized


def get_auth_client():
    """
    Create an AuthClient for the portal
    """
    return ConfidentialAppAuthClient(app.config['GLOBUS_CLIENT'], app.config['GLOBUS_KEY'])
