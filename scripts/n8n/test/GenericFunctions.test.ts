import { NodeApiError } from 'n8n-workflow';
import type { IExecuteFunctions, ILoadOptionsFunctions } from 'n8n-workflow';

import {
	bondruckerApiRequest,
	getIcons,
	getPresets,
	getTemplates,
} from '../nodes/Bondrucker/GenericFunctions';

function createMockContext(overrides: {
	httpRequestWithAuthentication?: jest.Mock;
	credentials?: Record<string, unknown>;
}): IExecuteFunctions {
	const credentials = overrides.credentials ?? {
		host: 'https://backend-bondrucker.bondrucker-app.de',
		apiKey: 'secret-key',
	};

	return {
		getCredentials: jest.fn().mockResolvedValue(credentials),
		getNode: jest.fn().mockReturnValue({ name: 'Bondrucker', type: 'bondrucker' }),
		helpers: {
			httpRequestWithAuthentication: overrides.httpRequestWithAuthentication,
		},
	} as unknown as IExecuteFunctions;
}

describe('bondruckerApiRequest', () => {
	it('sends the request via httpRequestWithAuthentication against {host}{endpoint}', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue({ id: '123', status: 'queued' });
		const context = createMockContext({ httpRequestWithAuthentication });

		const result = await bondruckerApiRequest.call(
			context,
			'POST',
			'/api/jobs',
			{ template: 'todo', title: 'Buy milk' },
		);

		expect(result).toEqual({ id: '123', status: 'queued' });
		expect(httpRequestWithAuthentication).toHaveBeenCalledTimes(1);

		const [credentialType, options] = httpRequestWithAuthentication.mock.calls[0];
		expect(credentialType).toBe('bondruckerApi');
		expect(options.method).toBe('POST');
		expect(options.url).toBe('https://backend-bondrucker.bondrucker-app.de/api/jobs');
		expect(options.body).toEqual({ template: 'todo', title: 'Buy milk' });
	});

	it('strips a trailing slash from the configured host', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue({ status: 'ok' });
		const context = createMockContext({
			httpRequestWithAuthentication,
			credentials: { host: 'https://backend-bondrucker.bondrucker-app.de/', apiKey: 'x' },
		});

		await bondruckerApiRequest.call(context, 'GET', '/health');

		expect(httpRequestWithAuthentication.mock.calls[0][1].url).toBe(
			'https://backend-bondrucker.bondrucker-app.de/health',
		);
	});

	it('omits body/qs from the request options when empty', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue([]);
		const context = createMockContext({ httpRequestWithAuthentication });

		await bondruckerApiRequest.call(context, 'GET', '/api/templates');

		const options = httpRequestWithAuthentication.mock.calls[0][1];
		expect(options.body).toBeUndefined();
		expect(options.qs).toBeUndefined();
	});

	it('passes qs through unmodified when provided', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue([]);
		const context = createMockContext({ httpRequestWithAuthentication });

		await bondruckerApiRequest.call(context, 'GET', '/api/jobs', {}, { status: 'queued' });

		expect(httpRequestWithAuthentication.mock.calls[0][1].qs).toEqual({ status: 'queued' });
	});

	it('merges extra request options (e.g. arraybuffer encoding for binary responses)', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(Buffer.from('png-bytes'));
		const context = createMockContext({ httpRequestWithAuthentication });

		await bondruckerApiRequest.call(context, 'POST', '/api/preview', { template: 'todo' }, {}, {
			json: false,
			encoding: 'arraybuffer',
		});

		const options = httpRequestWithAuthentication.mock.calls[0][1];
		expect(options.json).toBe(false);
		expect(options.encoding).toBe('arraybuffer');
	});

	it('throws a descriptive NodeApiError on HTTP 401 (bad API key)', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockRejectedValue({ statusCode: 401, message: 'Unauthorized' });
		const context = createMockContext({ httpRequestWithAuthentication });

		await expect(bondruckerApiRequest.call(context, 'GET', '/api/jobs')).rejects.toThrow(
			NodeApiError,
		);
		await expect(bondruckerApiRequest.call(context, 'GET', '/api/jobs')).rejects.toThrow(
			/authentication failed/i,
		);
	});

	it('wraps unexpected transport/HTTP errors in a generic NodeApiError', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockRejectedValue({ response: { statusCode: 404 }, message: 'Not Found' });
		const context = createMockContext({ httpRequestWithAuthentication });

		await expect(bondruckerApiRequest.call(context, 'GET', '/api/jobs/unknown')).rejects.toThrow(
			NodeApiError,
		);
	});
});

function createMockLoadOptionsFunctions(request: jest.Mock): ILoadOptionsFunctions {
	return {
		getCredentials: jest.fn().mockResolvedValue({
			host: 'https://backend-bondrucker.bondrucker-app.de',
			apiKey: 'secret-key',
		}),
		getNode: jest.fn().mockReturnValue({ name: 'Bondrucker', type: 'bondrucker' }),
		helpers: { httpRequestWithAuthentication: request },
	} as unknown as ILoadOptionsFunctions;
}

describe('loadOptions helpers', () => {
	it('getTemplates: maps and alphabetically sorts templates returned by GET /api/templates', async () => {
		const request = jest.fn().mockResolvedValue([
			{ key: 'zeta', name: 'Zeta', type: 'text' },
			{ key: 'todo', name: 'Todo', type: 'checklist' },
		]);
		const context = createMockLoadOptionsFunctions(request);

		const options = await getTemplates.call(context);

		expect(request.mock.calls[0][1]).toMatchObject({ method: 'GET', url: expect.stringContaining('/api/templates') });
		expect(options).toEqual([
			{ name: 'Todo (todo)', value: 'todo', description: 'Type: checklist' },
			{ name: 'Zeta (zeta)', value: 'zeta', description: 'Type: text' },
		]);
	});

	it('getPresets: maps and alphabetically sorts presets returned by GET /api/presets', async () => {
		const request = jest.fn().mockResolvedValue([
			{ key: 'news', name: 'News', category: 'Info', description: 'Daily news' },
			{ key: 'recipe', name: 'Recipe', category: 'Food', description: "Today's recipe" },
		]);
		const context = createMockLoadOptionsFunctions(request);

		const options = await getPresets.call(context);

		expect(options).toEqual([
			{ name: 'News (Info)', value: 'news', description: 'Daily news' },
			{ name: 'Recipe (Food)', value: 'recipe', description: "Today's recipe" },
		]);
	});

	it('getIcons: maps and alphabetically sorts icon names returned by GET /api/icons', async () => {
		const request = jest.fn().mockResolvedValue(['fa-cart-shopping', 'fa-bell', 'svg-logo']);
		const context = createMockLoadOptionsFunctions(request);

		const options = await getIcons.call(context);

		expect(options).toEqual([
			{ name: 'fa-bell', value: 'fa-bell' },
			{ name: 'fa-cart-shopping', value: 'fa-cart-shopping' },
			{ name: 'svg-logo', value: 'svg-logo' },
		]);
	});

	it('returns an empty list when the API responds with no data', async () => {
		const request = jest.fn().mockResolvedValue(undefined);
		const context = createMockLoadOptionsFunctions(request);

		await expect(getTemplates.call(context)).resolves.toEqual([]);
	});
});
