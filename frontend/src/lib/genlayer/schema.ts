import deployedSchema from "../../../../docs/deployed-schema.json";

export type ContractValue = string | number | string[];
export type ContractMethod = (typeof deployedSchema.methods)[number];
export type MethodName = ContractMethod["name"];

export const deployedContractSchema = deployedSchema;
export const viewMethods = deployedSchema.methods.filter((method) => method.readonly);
export const writeMethods = deployedSchema.methods.filter((method) => !method.readonly);

if (deployedSchema.constructor.params.length !== 0 || viewMethods.length !== 23 || writeMethods.length !== 17) {
  throw new Error("The deployed LACUNA schema snapshot is not the audited 40-method StudioNet schema.");
}

export function requireSchemaMethod(name: string, readonly: boolean): void {
  const method = deployedSchema.methods.find((candidate) => candidate.name === name);
  if (!method || method.readonly !== readonly) {
    throw new Error(`Deployed schema does not expose ${readonly ? "view" : "write"} method ${name}.`);
  }
}
