import type { IExecuteFunctions, INodeExecutionData } from 'n8n-workflow';

import { Bondrucker } from '../nodes/Bondrucker/Bondrucker.node';

type ParamMap = Record<string, unknown>;

/**
 * Builds a minimal IExecuteFunctions mock. `paramsByIndex[i]` holds the
 * node-parameter values for input item `i`, keyed by parameter name - this
 * mirrors how n8n resolves `getNodeParameter(name, itemIndex, fallback)`.
 * `resource`/`operation` are read once at index 0 by the node, so they only
 * need to be present in `paramsByIndex[0]`.
 */
function createMockExecuteFunctions(options: {
	items: INodeExecutionData[];
	paramsByIndex: ParamMap[];
	httpRequestWithAuthentication: jest.Mock;
	prepareBinaryData?: jest.Mock;
	continueOnFail?: boolean;
}): IExecuteFunctions {
	const {
		items,
		paramsByIndex,
		httpRequestWithAuthentication,
		prepareBinaryData,
		continueOnFail = false,
	} = options;

	return {
		getInputData: () => items,
		getNodeParameter: (name: string, itemIndex: number, fallback?: unknown) => {
			const params = paramsByIndex[itemIndex] ?? {};
			return Object.prototype.hasOwnProperty.call(params, name) ? params[name] : fallback;
		},
		getCredentials: jest.fn().mockResolvedValue({
			host: 'https://backend-bondrucker.bondrucker-app.de',
			apiKey: 'secret-key',
		}),
		getNode: jest.fn().mockReturnValue({ name: 'Bondrucker', type: 'bondrucker' }),
		continueOnFail: () => continueOnFail,
		helpers: {
			httpRequestWithAuthentication,
			prepareBinaryData:
				prepareBinaryData ??
				jest.fn().mockResolvedValue({ data: 'base64==', mimeType: 'image/png', fileName: 'preview.png' }),
		},
	} as unknown as IExecuteFunctions;
}

describe('Bondrucker node execute()', () => {
	const node = new Bondrucker();

	it('job:create sends template/title/markdown and additionalFields as the request body', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockResolvedValue({ id: 'job-1', status: 'queued' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [
				{
					resource: 'job',
					operation: 'create',
					template: 'todo',
					title: 'Einkaufsliste',
					markdown: '- [ ] Milch',
					additionalFields: { icon: 'fa-cart-shopping', print_timestamp: false },
				},
			],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(httpRequestWithAuthentication).toHaveBeenCalledTimes(1);
		const options = httpRequestWithAuthentication.mock.calls[0][1];
		expect(options.method).toBe('POST');
		expect(options.url).toBe('https://backend-bondrucker.bondrucker-app.de/api/jobs');
		expect(options.body).toEqual({
			template: 'todo',
			title: 'Einkaufsliste',
			markdown: '- [ ] Milch',
			icon: 'fa-cart-shopping',
			print_timestamp: false,
		});
		expect(result[0][0].json).toEqual({ id: 'job-1', status: 'queued' });
	});

	it('job:create omits optional fields that were left empty', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockResolvedValue({ id: 'job-2', status: 'queued' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [
				{ resource: 'job', operation: 'create', template: 'freitext', title: '', markdown: '' },
			],
			httpRequestWithAuthentication,
		});

		await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].body).toEqual({ template: 'freitext' });
	});

	it('job:get calls GET /api/jobs/{id} and returns the job object', async () => {
		const job = { id: 'job-3', status: 'printing' };
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(job);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'job', operation: 'get', jobId: 'job-3' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].url).toBe(
			'https://backend-bondrucker.bondrucker-app.de/api/jobs/job-3',
		);
		expect(result[0][0].json).toEqual(job);
	});

	it('job:getAll applies the status filter as a query param and slices by limit', async () => {
		const jobs = [{ id: '1' }, { id: '2' }, { id: '3' }];
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(jobs);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [
				{ resource: 'job', operation: 'getAll', returnAll: false, limit: 2, status: 'queued' },
			],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].qs).toEqual({ status: 'queued' });
		expect(result[0]).toHaveLength(2);
		expect(result[0].map((item) => item.json)).toEqual([{ id: '1' }, { id: '2' }]);
	});

	it('job:getAll omits the status query param when status is "all"', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue([{ id: '1' }]);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'job', operation: 'getAll', returnAll: true, status: 'all' }],
			httpRequestWithAuthentication,
		});

		await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].qs).toBeUndefined();
	});

	it('job:cancel calls DELETE /api/jobs/{id} and returns the cancelled job', async () => {
		const job = { id: 'job-4', status: 'cancelled' };
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(job);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'job', operation: 'cancel', jobId: 'job-4' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].method).toBe('DELETE');
		expect(httpRequestWithAuthentication.mock.calls[0][1].url).toBe(
			'https://backend-bondrucker.bondrucker-app.de/api/jobs/job-4',
		);
		expect(result[0][0].json).toEqual(job);
	});

	it('preset:getAll emits one item per configured preset', async () => {
		const presets = [{ key: 'a', name: 'A' }, { key: 'b', name: 'B' }];
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(presets);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'preset', operation: 'getAll' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(result[0].map((item) => item.json)).toEqual(presets);
	});

	it('preset:print calls POST /api/presets/{key}/print and returns the created job', async () => {
		const job = { id: 'job-5', status: 'queued' };
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(job);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'preset', operation: 'print', key: 'wlan-qrcode' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].method).toBe('POST');
		expect(httpRequestWithAuthentication.mock.calls[0][1].url).toBe(
			'https://backend-bondrucker.bondrucker-app.de/api/presets/wlan-qrcode/print',
		);
		expect(result[0][0].json).toEqual(job);
	});

	it.each([
		['status', 'GET', '/api/printer/status'],
		['power', 'GET', '/api/printer/power'],
		['toggle', 'POST', '/api/printer/power/toggle'],
	])('printer:%s calls %s %s', async (operation, method, path) => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue({ ok: true });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'printer', operation }],
			httpRequestWithAuthentication,
		});

		await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].method).toBe(method);
		expect(httpRequestWithAuthentication.mock.calls[0][1].url).toBe(
			`https://backend-bondrucker.bondrucker-app.de${path}`,
		);
	});

	it('template:getAll emits one item per configured template', async () => {
		const templates = [{ key: 'todo', name: 'Todo' }];
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(templates);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'template', operation: 'getAll' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(result[0].map((item) => item.json)).toEqual(templates);
	});

	it('icon:getAll wraps each icon name string as { name }', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(['fa-bell', 'svg-logo']);
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'icon', operation: 'getAll' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(result[0].map((item) => item.json)).toEqual([{ name: 'fa-bell' }, { name: 'svg-logo' }]);
	});

	it('health:check calls GET /health', async () => {
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue({ status: 'ok' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'health', operation: 'check' }],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(httpRequestWithAuthentication.mock.calls[0][1].url).toBe(
			'https://backend-bondrucker.bondrucker-app.de/health',
		);
		expect(result[0][0].json).toEqual({ status: 'ok' });
	});

	it('preview:create requests a binary PNG and attaches it under the configured binary property', async () => {
		const pngBuffer = Buffer.from('fake-png-bytes');
		const httpRequestWithAuthentication = jest.fn().mockResolvedValue(pngBuffer);
		const prepareBinaryData = jest
			.fn()
			.mockResolvedValue({ data: 'ZmFrZS1wbmctYnl0ZXM=', mimeType: 'image/png', fileName: 'preview.png' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [
				{
					resource: 'preview',
					operation: 'create',
					template: 'todo',
					title: 'Test',
					binaryPropertyName: 'data',
				},
			],
			httpRequestWithAuthentication,
			prepareBinaryData,
		});

		const result = await node.execute.call(context);

		const options = httpRequestWithAuthentication.mock.calls[0][1];
		expect(options.url).toBe('https://backend-bondrucker.bondrucker-app.de/api/preview');
		expect(options.json).toBe(false);
		expect(options.encoding).toBe('arraybuffer');
		expect(prepareBinaryData).toHaveBeenCalledWith(pngBuffer, 'preview.png', 'image/png');
		expect(result[0][0].binary?.data).toEqual({
			data: 'ZmFrZS1wbmctYnl0ZXM=',
			mimeType: 'image/png',
			fileName: 'preview.png',
		});
	});

	it('propagates API errors when continueOnFail is false', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockRejectedValue({ statusCode: 401, message: 'Unauthorized' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'job', operation: 'get', jobId: '1' }],
			httpRequestWithAuthentication,
			continueOnFail: false,
		});

		await expect(node.execute.call(context)).rejects.toBeTruthy();
	});

	it('captures API errors as item JSON when continueOnFail is true', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockRejectedValue({ statusCode: 401, message: 'Unauthorized' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }],
			paramsByIndex: [{ resource: 'job', operation: 'get', jobId: '1' }],
			httpRequestWithAuthentication,
			continueOnFail: true,
		});

		const result = await node.execute.call(context);

		expect(result[0]).toHaveLength(1);
		expect(result[0][0].json.error).toBeDefined();
	});

	it('processes multiple input items independently', async () => {
		const httpRequestWithAuthentication = jest
			.fn()
			.mockResolvedValueOnce({ id: 'a' })
			.mockResolvedValueOnce({ id: 'b' });
		const context = createMockExecuteFunctions({
			items: [{ json: {} }, { json: {} }],
			paramsByIndex: [
				{ resource: 'job', operation: 'get', jobId: 'a' },
				{ resource: 'job', operation: 'get', jobId: 'b' },
			],
			httpRequestWithAuthentication,
		});

		const result = await node.execute.call(context);

		expect(result[0]).toHaveLength(2);
		expect(result[0][0].json).toEqual({ id: 'a' });
		expect(result[0][1].json).toEqual({ id: 'b' });
	});
});
