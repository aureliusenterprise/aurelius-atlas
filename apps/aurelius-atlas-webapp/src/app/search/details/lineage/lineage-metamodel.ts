/**
 * The human-readable type names of the model's concept types (LDG-20, LDG-37
 * via DD-418): the whole `archimate3` slice of the legacy metamodel
 * (`libs/metamodel/src/lib/metamodel.ts` — its `elements` and
 * `relations_by_tag` tables, verbatim) plus the view type, whose name the
 * legacy parser hardcodes (`parse-view.ts`: type `ar3_View`, human-readable
 * "View"). The 7.22b table carried only the four types the shipped producer
 * emits; 7.22e's archimate port brings the rest, so a drawer opened over an
 * archimate document names its types as the legacy did.
 *
 * An unknown type reads as the empty string (the legacy's dictionary lookup
 * answered `undefined`; the panel hides the Type row when its value is
 * empty). `ar3_Element` and `ar3_Junction` carry no name, as in the legacy —
 * a bare element or junction types as unknown.
 */
const HUMAN_READABLE_TYPES: Readonly<Record<string, string>> = {
    ar3_AndJunction: "And Junction",
    ar3_ApplicationCollaboration: "Application Collaboration",
    ar3_ApplicationComponent: "Application Component",
    ar3_ApplicationEvent: "Application Event",
    ar3_ApplicationFunction: "Application Function",
    ar3_ApplicationInteraction: "Application Interaction",
    ar3_ApplicationInterface: "Application Interface",
    ar3_ApplicationProcess: "Application Process",
    ar3_ApplicationService: "Application Service",
    ar3_Artifact: "Artifact",
    ar3_Assessment: "Assessment",
    ar3_BusinessActor: "Business Actor",
    ar3_BusinessCollaboration: "Business Collaboration",
    ar3_BusinessEvent: "Business Event",
    ar3_BusinessFunction: "Business Function",
    ar3_BusinessInteraction: "Business Interaction",
    ar3_BusinessInterface: "Business Interface",
    ar3_BusinessObject: "Business Object",
    ar3_BusinessProcess: "Business Process",
    ar3_BusinessRole: "Business Role",
    ar3_BusinessService: "Business Service",
    ar3_Capability: "Capability",
    ar3_CommunicationNetwork: "Communication Network",
    ar3_Constraint: "Constraint",
    ar3_Contract: "Contract",
    ar3_CourseOfAction: "Course of Action",
    ar3_DataObject: "Data Object",
    ar3_Deliverable: "Deliverable",
    ar3_Device: "Device",
    ar3_DistributionNetwork: "Distribution Network",
    ar3_Driver: "Driver",
    ar3_Equipment: "Equipment",
    ar3_Facility: "Facility",
    ar3_Gap: "Gap",
    ar3_Goal: "Goal",
    ar3_Grouping: "Grouping",
    ar3_ImplementationEvent: "Implementation Event",
    ar3_Location: "Location",
    ar3_Material: "Material",
    ar3_Meaning: "Meaning",
    ar3_Node: "Node",
    ar3_OrJunction: "Or Junction",
    ar3_Outcome: "Outcome",
    ar3_Path: "Path",
    ar3_Plateau: "Plateau",
    ar3_Principle: "Principle",
    ar3_Product: "Product",
    ar3_Representation: "Representation",
    ar3_Requirement: "Requirement",
    ar3_Resource: "Resource",
    ar3_Stakeholder: "Stakeholder",
    ar3_SystemSoftware: "System Software",
    ar3_TechnologyCollaboration: "Technology Collaboration",
    ar3_TechnologyEvent: "Technology Event",
    ar3_TechnologyFunction: "Technology Function",
    ar3_TechnologyInteraction: "Technology Interaction",
    ar3_TechnologyInterface: "Technology Interface",
    ar3_TechnologyProcess: "Technology Process",
    ar3_TechnologyService: "Technology Service",
    ar3_Unknown: "-- Please select a type --",
    ar3_Value: "Value",
    ar3_ValueStream: "Value Stream",
    ar3_WorkPackage: "Work Package",
    lineage_dataset: "Dataset",
    lineage_process: "Process",
    lineage_relation: "Data Lineage",
    ar3_Access: "Access",
    ar3_Aggregation: "Aggregation",
    ar3_Assignment: "Assignment",
    ar3_Association: "Association",
    ar3_Composition: "Composition",
    ar3_Flow: "Flow",
    ar3_Influence: "Influence",
    ar3_Realization: "Realization",
    ar3_Serving: "Serving",
    ar3_Specialization: "Specialization",
    ar3_Triggering: "Triggering",
    ar3_View: "View",
};

/**
 * The display name of a concept type (the legacy's `archimate3[...]` lookup).
 * @param type the concept's `@xsi_type` (or parser type, for a view)
 * @returns the human-readable name, or the empty string when unknown
 */
export function humanReadableType(type: string): string {
    return HUMAN_READABLE_TYPES[type] ?? "";
}

/**
 * The relation types' verb phrases (DD-411, DD-418): the legacy
 * `parsers/archimate3/parse-relation.ts` `humanReadableTypes` table in full —
 * the `displayName` the relationship row's middle line leads with when the
 * relation carries no name of its own. 7.22b carried only the shipped chain's
 * `lineage_relation`; the archimate verbs joined with the 7.22e port. An
 * unknown type reads as the empty string (the legacy's dictionary answered
 * `undefined`, and the row hid the span).
 */
const RELATION_VERBS: Readonly<Record<string, string>> = {
    ar3_Access: "Accesses",
    ar3_Aggregation: "Aggregates",
    ar3_Assignment: "Assigned to",
    ar3_Association: "Associated with",
    ar3_Composition: "Composes",
    ar3_Flow: "Flows into",
    ar3_Influence: "Influences",
    ar3_Realization: "Realizes",
    ar3_Serving: "Serves",
    ar3_Specialization: "Specializes",
    ar3_Triggering: "Triggers",
    lineage_relation: "Flows into",
};

/**
 * The verb phrase of a relation type (the legacy parser's `displayName`).
 * @param type the relation's `@xsi_type`
 * @returns the verb phrase, or the empty string when unknown
 */
export function relationVerb(type: string): string {
    return RELATION_VERBS[type] ?? "";
}
