import type {
	IDataObject,
	IExecuteFunctions,
	IHttpRequestMethods,
	IHttpRequestOptions,
	ILoadOptionsFunctions,
	INodePropertyOptions,
	JsonObject,
} from 'n8n-workflow';
import { NodeApiError } from 'n8n-workflow';

/**
 * Bondrucker exposes a plain REST API (see `docs/openapi.yaml`) authenticated
 * via the "X-API-Key" header - the credential's declarative `authenticate`
 * (see `credentials/BondruckerApi.credentials.ts`) adds that header to every
 * request made through `httpRequestWithAuthentication`.
 */
export async function bondruckerApiRequest(
	this: IExecuteFunctions | ILoadOptionsFunctions,
	method: IHttpRequestMethods,
	endpoint: string,
	body: IDataObject = {},
	qs: IDataObject = {},
	option: Partial<IHttpRequestOptions> = {},
): Promise<any> {
	const credentials = await this.getCredentials('bondruckerApi');
	const host = (credentials.host as string).replace(/\/+$/, '');

	const requestOptions: IHttpRequestOptions = {
		method,
		url: `${host}${endpoint}`,
		json: true,
		body,
		qs,
		...option,
	};

	if (Object.keys(body).length === 0) {
		delete requestOptions.body;
	}
	if (Object.keys(qs).length === 0) {
		delete requestOptions.qs;
	}

	try {
		return await this.helpers.httpRequestWithAuthentication.call(
			this,
			'bondruckerApi',
			requestOptions,
		);
	} catch (error) {
		const statusCode =
			(error as JsonObject).statusCode ??
			((error as JsonObject).response as JsonObject | undefined)?.statusCode;

		if (statusCode === 401) {
			throw new NodeApiError(this.getNode(), error as JsonObject, {
				message: 'Bondrucker authentication failed (401)',
				description:
					'Check the "API Key" field in the Bondrucker credentials against the backend\'s ' +
					'API_KEY setting (see .env.example).',
				httpCode: '401',
			});
		}

		throw new NodeApiError(this.getNode(), error as JsonObject, {
			message: `Bondrucker API request failed (${method} ${endpoint})`,
		});
	}
}

export async function getTemplates(
	this: ILoadOptionsFunctions,
): Promise<INodePropertyOptions[]> {
	const templates = ((await bondruckerApiRequest.call(
		this,
		'GET',
		'/api/templates',
	)) as IDataObject[]) ?? [];

	return templates
		.map((template) => ({
			name: `${template.name as string} (${template.key as string})`,
			value: String(template.key),
			description: `Type: ${template.type as string}`,
		}))
		.sort((a, b) => a.name.localeCompare(b.name));
}

export async function getPresets(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
	const presets = ((await bondruckerApiRequest.call(
		this,
		'GET',
		'/api/presets',
	)) as IDataObject[]) ?? [];

	return presets
		.map((preset) => ({
			name: `${preset.name as string} (${preset.category as string})`,
			value: String(preset.key),
			description: preset.description as string,
		}))
		.sort((a, b) => a.name.localeCompare(b.name));
}

export async function getIcons(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
	const icons = ((await bondruckerApiRequest.call(this, 'GET', '/api/icons')) as string[]) ?? [];

	return icons
		.map((icon) => ({ name: icon, value: icon }))
		.sort((a, b) => a.name.localeCompare(b.name));
}
