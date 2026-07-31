import type {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeConnectionTypes } from 'n8n-workflow';

import { bondruckerApiRequest, getIcons, getPresets, getTemplates } from './GenericFunctions';

const JOB_STATUSES = ['queued', 'printing', 'failed', 'completed', 'cancelled'] as const;

/**
 * Builds the `PrintJobCreate` request body (see `backend/app/schemas.py`)
 * shared by "Job: Create" (`POST /api/jobs`) and "Preview: Render"
 * (`POST /api/preview`) - both take the exact same payload shape.
 */
function buildJobPayload(context: IExecuteFunctions, itemIndex: number): IDataObject {
	const template = context.getNodeParameter('template', itemIndex) as string;
	const title = context.getNodeParameter('title', itemIndex, '') as string;
	const markdown = context.getNodeParameter('markdown', itemIndex, '') as string;
	const additionalFields = context.getNodeParameter(
		'additionalFields',
		itemIndex,
		{},
	) as IDataObject;

	const body: IDataObject = { template };
	if (title) {
		body.title = title;
	}
	if (markdown) {
		body.markdown = markdown;
	}
	if (additionalFields.icon) {
		body.icon = additionalFields.icon;
	}
	if (typeof additionalFields.print_timestamp === 'boolean') {
		body.print_timestamp = additionalFields.print_timestamp;
	}
	if (additionalFields.image_base64) {
		body.image_base64 = additionalFields.image_base64;
	}
	if (additionalFields.qr_code) {
		body.qr_code = additionalFields.qr_code;
	}

	return body;
}

export class Bondrucker implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Bondrucker',
		name: 'bondrucker',
		icon: 'file:bondrucker.png',
		group: ['output'],
		version: 1,
		subtitle: '={{$parameter["operation"] + ": " + $parameter["resource"]}}',
		description:
			'Create print jobs, trigger presets, and check printer status on a Bondrucker ESC/POS thermal-printer backend',
		defaults: {
			name: 'Bondrucker',
		},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		credentials: [
			{
				name: 'bondruckerApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Resource',
				name: 'resource',
				type: 'options',
				noDataExpression: true,
				options: [
					{ name: 'Health', value: 'health' },
					{ name: 'Icon', value: 'icon' },
					{ name: 'Job', value: 'job' },
					{ name: 'Preset', value: 'preset' },
					{ name: 'Preview', value: 'preview' },
					{ name: 'Printer', value: 'printer' },
					{ name: 'Template', value: 'template' },
				],
				default: 'job',
			},

			// ------------------------------- operations -------------------------------
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['job'],
					},
				},
				options: [
					{
						name: 'Cancel',
						value: 'cancel',
						description: 'Cancel a queued or failed print job',
						action: 'Cancel a job',
					},
					{
						name: 'Create',
						value: 'create',
						description: 'Validate and enqueue a new print job',
						action: 'Create a job',
					},
					{
						name: 'Get',
						value: 'get',
						description: 'Get a single print job by ID',
						action: 'Get a job',
					},
					{
						name: 'Get Many',
						value: 'getAll',
						description: 'Get many print jobs, optionally filtered by status',
						action: 'Get many jobs',
					},
				],
				default: 'create',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['preset'],
					},
				},
				options: [
					{
						name: 'Get Many',
						value: 'getAll',
						description: 'List the configured standard print objects (Standarddruckobjekte)',
						action: 'Get many presets',
					},
					{
						name: 'Print',
						value: 'print',
						description: 'Resolve a preset to a print job and enqueue it',
						action: 'Print a preset',
					},
				],
				default: 'getAll',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['printer'],
					},
				},
				options: [
					{
						name: 'Get Power',
						value: 'power',
						description: 'Get the current power state of the printer plug',
						action: 'Get printer power state',
					},
					{
						name: 'Get Status',
						value: 'status',
						description: 'Report printer connectivity and the current queue state',
						action: 'Get printer status',
					},
					{
						name: 'Toggle Power',
						value: 'toggle',
						description: 'Toggle the printer plug via Home Assistant',
						action: 'Toggle printer power',
					},
				],
				default: 'status',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['template'],
					},
				},
				options: [
					{
						name: 'Get Many',
						value: 'getAll',
						description: 'List the configured print templates',
						action: 'Get many templates',
					},
				],
				default: 'getAll',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['icon'],
					},
				},
				options: [
					{
						name: 'Get Many',
						value: 'getAll',
						description: 'List the icon names available for print jobs',
						action: 'Get many icons',
					},
				],
				default: 'getAll',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['preview'],
					},
				},
				options: [
					{
						name: 'Create',
						value: 'create',
						description: 'Render a print job payload to a PNG preview without enqueueing it',
						action: 'Render a preview',
					},
				],
				default: 'create',
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['health'],
					},
				},
				options: [
					{
						name: 'Check',
						value: 'check',
						description: 'Simple liveness probe, does not require an API key',
						action: 'Check backend health',
					},
				],
				default: 'check',
			},

			// ------------------------------- job:create / preview:create -------------------------------
			{
				displayName: 'Template Name or ID',
				name: 'template',
				type: 'options',
				typeOptions: {
					loadOptionsMethod: 'getTemplates',
				},
				default: '',
				required: true,
				displayOptions: {
					show: {
						resource: ['job', 'preview'],
						operation: ['create'],
					},
				},
				description:
					'Key of a configured print template. Choose from the list, or specify an ID using an expression.',
			},
			{
				displayName: 'Title',
				name: 'title',
				type: 'string',
				default: '',
				displayOptions: {
					show: {
						resource: ['job', 'preview'],
						operation: ['create'],
					},
				},
				description: 'Title printed above the content',
			},
			{
				displayName: 'Markdown',
				name: 'markdown',
				type: 'string',
				typeOptions: { rows: 6 },
				default: '',
				displayOptions: {
					show: {
						resource: ['job', 'preview'],
						operation: ['create'],
					},
				},
				description: 'Markdown content of the print job',
			},
			{
				displayName: 'Additional Fields',
				name: 'additionalFields',
				type: 'collection',
				placeholder: 'Add Field',
				default: {},
				displayOptions: {
					show: {
						resource: ['job', 'preview'],
						operation: ['create'],
					},
				},
				options: [
					{
						displayName: 'Icon Name or ID',
						name: 'icon',
						type: 'options',
						typeOptions: {
							loadOptionsMethod: 'getIcons',
						},
						default: '',
						description:
							'Icon printed next to the title, e.g. "fa-cart-shopping" (Font Awesome) or "svg-logo" ' +
							'(custom SVG). Choose from the list, or specify an ID using an expression.',
					},
					{
						displayName: 'Image (Base64)',
						name: 'image_base64',
						type: 'string',
						default: '',
						typeOptions: { rows: 2 },
						description:
							'Base64-encoded image (optionally a "data:" URL), printed after the title as black & ' +
							'white. Mutually exclusive with QR Code.',
					},
					{
						displayName: 'Print Timestamp',
						name: 'print_timestamp',
						type: 'boolean',
						default: true,
						description: 'Whether to print the current date/time in the bottom-right corner',
					},
					{
						displayName: 'QR Code',
						name: 'qr_code',
						type: 'string',
						default: '',
						description:
							'Content to encode as a QR code (URL, WLAN, vCard, geo-location, ...), printed after ' +
							'the title. Mutually exclusive with Image (Base64).',
					},
				],
			},

			// ------------------------------- preview:create -------------------------------
			{
				displayName: 'Output Binary Field',
				name: 'binaryPropertyName',
				type: 'string',
				default: 'data',
				required: true,
				displayOptions: {
					show: {
						resource: ['preview'],
						operation: ['create'],
					},
				},
				description: 'Name of the binary property the rendered PNG preview is written to',
			},

			// ------------------------------- job:get / cancel -------------------------------
			{
				displayName: 'Job ID',
				name: 'jobId',
				type: 'string',
				default: '',
				required: true,
				displayOptions: {
					show: {
						resource: ['job'],
						operation: ['get', 'cancel'],
					},
				},
				description: 'ID of the print job',
			},

			// ------------------------------- job:getAll -------------------------------
			{
				displayName: 'Return All',
				name: 'returnAll',
				type: 'boolean',
				default: false,
				displayOptions: {
					show: {
						resource: ['job'],
						operation: ['getAll'],
					},
				},
				description: 'Whether to return all results or only up to a given limit',
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				default: 50,
				typeOptions: { minValue: 1 },
				displayOptions: {
					show: {
						resource: ['job'],
						operation: ['getAll'],
						returnAll: [false],
					},
				},
				description: 'Max number of results to return',
			},
			{
				displayName: 'Status',
				name: 'status',
				type: 'options',
				default: 'all',
				displayOptions: {
					show: {
						resource: ['job'],
						operation: ['getAll'],
					},
				},
				options: [
					{ name: 'All', value: 'all' },
					{ name: 'Cancelled', value: 'cancelled' },
					{ name: 'Completed', value: 'completed' },
					{ name: 'Failed', value: 'failed' },
					{ name: 'Printing', value: 'printing' },
					{ name: 'Queued', value: 'queued' },
				],
				description: 'Only return jobs with this status',
			},

			// ------------------------------- preset:print -------------------------------
			{
				displayName: 'Preset Name or ID',
				name: 'key',
				type: 'options',
				typeOptions: {
					loadOptionsMethod: 'getPresets',
				},
				default: '',
				required: true,
				displayOptions: {
					show: {
						resource: ['preset'],
						operation: ['print'],
					},
				},
				description:
					'Key of the configured standard print object. Choose from the list, or specify an ID ' +
					'using an expression.',
			},
		],
	};

	methods = {
		loadOptions: {
			getTemplates,
			getPresets,
			getIcons,
		},
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const resource = this.getNodeParameter('resource', 0) as string;
		const operation = this.getNodeParameter('operation', 0) as string;

		for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
			try {
				if (resource === 'job') {
					if (operation === 'create') {
						const body = buildJobPayload(this, itemIndex);
						const responseData = await bondruckerApiRequest.call(this, 'POST', '/api/jobs', body);
						returnData.push({ json: responseData as IDataObject, pairedItem: { item: itemIndex } });
					} else if (operation === 'get') {
						const jobId = this.getNodeParameter('jobId', itemIndex) as string;
						const responseData = await bondruckerApiRequest.call(
							this,
							'GET',
							`/api/jobs/${jobId}`,
						);
						returnData.push({ json: responseData as IDataObject, pairedItem: { item: itemIndex } });
					} else if (operation === 'getAll') {
						const returnAll = this.getNodeParameter('returnAll', itemIndex, false) as boolean;
						const status = this.getNodeParameter('status', itemIndex, 'all') as
							| (typeof JOB_STATUSES)[number]
							| 'all';

						const qs: IDataObject = {};
						if (status !== 'all') {
							qs.status = status;
						}

						let jobs = ((await bondruckerApiRequest.call(
							this,
							'GET',
							'/api/jobs',
							{},
							qs,
						)) as IDataObject[]) ?? [];

						if (!returnAll) {
							const limit = this.getNodeParameter('limit', itemIndex, 50) as number;
							jobs = jobs.slice(0, limit);
						}

						for (const job of jobs) {
							returnData.push({ json: job, pairedItem: { item: itemIndex } });
						}
						continue;
					} else if (operation === 'cancel') {
						const jobId = this.getNodeParameter('jobId', itemIndex) as string;
						const responseData = await bondruckerApiRequest.call(
							this,
							'DELETE',
							`/api/jobs/${jobId}`,
						);
						returnData.push({ json: responseData as IDataObject, pairedItem: { item: itemIndex } });
					} else {
						throw new Error(`Unsupported operation "${operation}" for resource "job"`);
					}
				} else if (resource === 'preset') {
					if (operation === 'getAll') {
						const presets = ((await bondruckerApiRequest.call(
							this,
							'GET',
							'/api/presets',
						)) as IDataObject[]) ?? [];

						for (const preset of presets) {
							returnData.push({ json: preset, pairedItem: { item: itemIndex } });
						}
						continue;
					} else if (operation === 'print') {
						const key = this.getNodeParameter('key', itemIndex) as string;
						const responseData = await bondruckerApiRequest.call(
							this,
							'POST',
							`/api/presets/${key}/print`,
						);
						returnData.push({ json: responseData as IDataObject, pairedItem: { item: itemIndex } });
					} else {
						throw new Error(`Unsupported operation "${operation}" for resource "preset"`);
					}
				} else if (resource === 'printer') {
					let responseData: unknown;
					if (operation === 'status') {
						responseData = await bondruckerApiRequest.call(this, 'GET', '/api/printer/status');
					} else if (operation === 'power') {
						responseData = await bondruckerApiRequest.call(this, 'GET', '/api/printer/power');
					} else if (operation === 'toggle') {
						responseData = await bondruckerApiRequest.call(
							this,
							'POST',
							'/api/printer/power/toggle',
						);
					} else {
						throw new Error(`Unsupported operation "${operation}" for resource "printer"`);
					}
					returnData.push({ json: responseData as IDataObject, pairedItem: { item: itemIndex } });
				} else if (resource === 'template') {
					if (operation !== 'getAll') {
						throw new Error(`Unsupported operation "${operation}" for resource "template"`);
					}
					const templates = ((await bondruckerApiRequest.call(
						this,
						'GET',
						'/api/templates',
					)) as IDataObject[]) ?? [];

					for (const template of templates) {
						returnData.push({ json: template, pairedItem: { item: itemIndex } });
					}
					continue;
				} else if (resource === 'icon') {
					if (operation !== 'getAll') {
						throw new Error(`Unsupported operation "${operation}" for resource "icon"`);
					}
					const icons = ((await bondruckerApiRequest.call(this, 'GET', '/api/icons')) as
						| string[]
						| undefined) ?? [];

					for (const icon of icons) {
						returnData.push({ json: { name: icon }, pairedItem: { item: itemIndex } });
					}
					continue;
				} else if (resource === 'preview') {
					if (operation !== 'create') {
						throw new Error(`Unsupported operation "${operation}" for resource "preview"`);
					}
					const body = buildJobPayload(this, itemIndex);
					const binaryPropertyName = this.getNodeParameter(
						'binaryPropertyName',
						itemIndex,
						'data',
					) as string;

					const pngBuffer = (await bondruckerApiRequest.call(this, 'POST', '/api/preview', body, {}, {
						json: false,
						encoding: 'arraybuffer',
					})) as Buffer;

					const binaryData = await this.helpers.prepareBinaryData(
						Buffer.from(pngBuffer),
						'preview.png',
						'image/png',
					);

					returnData.push({
						json: {},
						binary: { [binaryPropertyName]: binaryData },
						pairedItem: { item: itemIndex },
					});
				} else if (resource === 'health') {
					if (operation !== 'check') {
						throw new Error(`Unsupported operation "${operation}" for resource "health"`);
					}
					const responseData = await bondruckerApiRequest.call(this, 'GET', '/health');
					returnData.push({ json: responseData as IDataObject, pairedItem: { item: itemIndex } });
				} else {
					throw new Error(`Unsupported resource "${resource}"`);
				}
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: { error: (error as Error).message },
						pairedItem: { item: itemIndex },
					});
					continue;
				}
				throw error;
			}
		}

		return [returnData];
	}
}
