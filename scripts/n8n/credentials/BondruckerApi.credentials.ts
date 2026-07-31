import type {
	IAuthenticateGeneric,
	ICredentialTestRequest,
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class BondruckerApi implements ICredentialType {
	name = 'bondruckerApi';

	displayName = 'Bondrucker API';

	properties: INodeProperties[] = [
		{
			displayName: 'Host',
			name: 'host',
			type: 'string',
			default: 'https://backend-bondrucker.bondrucker-app.de',
			placeholder: 'https://backend-bondrucker.bondrucker-app.de',
			description: 'Base URL of the Bondrucker backend, without a trailing slash',
			required: true,
		},
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			description:
				'Value the backend expects in the "X-API-Key" header (matches the backend\'s API_KEY setting)',
			required: true,
		},
	];

	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {
			headers: {
				'X-API-Key': '={{$credentials.apiKey}}',
			},
		},
	};

	test: ICredentialTestRequest = {
		request: {
			baseURL: '={{$credentials.host}}',
			url: '/api/templates',
			method: 'GET',
		},
	};
}
