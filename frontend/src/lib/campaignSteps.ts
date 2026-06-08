export const PIPELINE_STEPS = [
  { key: "parse_brief",        label: "Parsing campaign brief"    },
  { key: "fetch_customers",    label: "Fetching customer data"    },
  { key: "segmentation",       label: "Segmenting customers"      },
  { key: "strategy",           label: "Generating campaign strategy" },
  { key: "content_generation", label: "Creating email content"    },
  { key: "approval",           label: "Checking approval status"  },
  { key: "wait_approval",      label: "Waiting for human approval" },
  { key: "execution",          label: "Executing campaign"        },
] as const;

export type PipelineStepKey = (typeof PIPELINE_STEPS)[number]["key"];
