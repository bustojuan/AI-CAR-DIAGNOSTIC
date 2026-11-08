export interface paths {
  "/api/v1/health": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Health */
    get: operations["health_api_v1_health_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Vehicles */
    get: operations["list_vehicles_api_v1_vehicles_get"];
    put?: never;
    /** Create Vehicle */
    post: operations["create_vehicle_api_v1_vehicles_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/cases": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Cases */
    get: operations["list_cases_api_v1_vehicles__vehicle_id__cases_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/urgency": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Vehicle Urgency */
    get: operations["vehicle_urgency_api_v1_vehicles__vehicle_id__urgency_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/case-history": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Case History */
    get: operations["case_history_api_v1_vehicles__vehicle_id__case_history_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Vehicle */
    get: operations["get_vehicle_api_v1_vehicles__vehicle_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Update Vehicle */
    patch: operations["update_vehicle_api_v1_vehicles__vehicle_id__patch"];
    trace?: never;
  };
  "/api/v1/conversations": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Create Conversation */
    post: operations["create_conversation_api_v1_conversations_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/conversations/{conversation_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Conversation */
    get: operations["get_conversation_api_v1_conversations__conversation_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/conversations/{conversation_id}/resolve": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Resolve Case */
    post: operations["resolve_case_api_v1_conversations__conversation_id__resolve_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/conversations/{conversation_id}/reopen": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Reopen Case */
    post: operations["reopen_case_api_v1_conversations__conversation_id__reopen_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/conversations/{conversation_id}/messages": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Add Message */
    post: operations["add_message_api_v1_conversations__conversation_id__messages_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/diagnostics": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Create Diagnostic */
    post: operations["create_diagnostic_api_v1_diagnostics_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/diagnostics/{diagnostic_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Diagnostic */
    get: operations["get_diagnostic_api_v1_diagnostics__diagnostic_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/documents/upload": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Upload */
    post: operations["upload_api_v1_documents_upload_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/documents/sources": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Sources */
    get: operations["sources_api_v1_documents_sources_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/documents": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Documents */
    get: operations["documents_api_v1_documents_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/documents/{document_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Document */
    get: operations["document_api_v1_documents__document_id__get"];
    put?: never;
    post?: never;
    /** Delete Document */
    delete: operations["delete_document_api_v1_documents__document_id__delete"];
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/documents/{document_id}/index": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Index Document */
    post: operations["index_document_api_v1_documents__document_id__index_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/retrieval/search": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Search */
    post: operations["search_api_v1_retrieval_search_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/retrieval/status": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Status */
    get: operations["status_api_v1_retrieval_status_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/retrieval/stats": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stats */
    get: operations["stats_api_v1_retrieval_stats_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/tools/status": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Status */
    get: operations["status_api_v1_tools_status_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/parts/search": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Search */
    post: operations["search_api_v1_parts_search_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/parts/compatibility": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Compatibility */
    post: operations["compatibility_api_v1_parts_compatibility_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/parts/prices": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Prices */
    post: operations["prices_api_v1_parts_prices_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AutomotiveResult */
    AutomotiveResult: {
      /**
       * Tool
       * @enum {string}
       */
      tool: "search_parts" | "check_compatibility" | "get_part_prices";
      /**
       * Execution Id
       * Format: uuid
       */
      execution_id?: string;
      /** Available */
      available: boolean;
      /** Reason */
      reason: string;
      /**
       * Provider
       * @enum {string}
       */
      provider: "unavailable" | "demo" | "ebay" | "ebay_sandbox";
      /** Demo Data */
      demo_data: boolean;
      /**
       * Verification
       * @enum {string}
       */
      verification: "unavailable" | "synthetic" | "verified_provider";
      /**
       * Retrieved At
       * Format: date-time
       */
      retrieved_at?: string;
      /** Error Category */
      error_category?:
        | (
            | "timeout"
            | "provider_failure"
            | "invalid_response"
            | "mcp_unavailable"
          )
        | null;
      /** Parts */
      parts?: components["schemas"]["Part"][];
      /** Prices */
      prices?: components["schemas"]["Price"][];
      /** Part Id */
      part_id?: string | null;
      /** Vehicle Id */
      vehicle_id?: string | null;
      /**
       * Compatibility
       * @default unknown
       * @enum {string}
       */
      compatibility:
        | "confirmed_compatible"
        | "confirmed_incompatible"
        | "requires_additional_information"
        | "unknown";
      /** Evidence */
      evidence?: string[];
      /** Missing Information */
      missing_information?: string[];
    };
    /** Body_upload_api_v1_documents_upload_post */
    Body_upload_api_v1_documents_upload_post: {
      /** Metadata */
      metadata: string;
      /** File */
      file: string;
      /**
       * Source Page Start
       * @default 1
       */
      source_page_start: number;
    };
    /** CaseHistory */
    CaseHistory: {
      /** Cases */
      cases: components["schemas"]["CaseSummary"][];
      vehicle_urgency: components["schemas"]["VehicleUrgency"];
    };
    /** CaseSummary */
    CaseSummary: {
      /**
       * Conversation Id
       * Format: uuid
       */
      conversation_id: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Resolution Status
       * @enum {string}
       */
      resolution_status: "active" | "resolved";
      /** Resolved At */
      resolved_at: string | null;
      /** Resolution Note */
      resolution_note: string | null;
      /**
       * Latest Diagnostic Id
       * Format: uuid
       */
      latest_diagnostic_id: string;
      /**
       * Latest Assessment At
       * Format: date-time
       */
      latest_assessment_at: string;
      /** Summary */
      summary: string;
      /** Assessment Count */
      assessment_count: number;
      historical_urgency: components["schemas"]["Urgency"];
    };
    /** CaseVersion */
    CaseVersion: {
      /**
       * Expected Latest Diagnostic Id
       * Format: uuid
       */
      expected_latest_diagnostic_id: string;
    };
    /** Check */
    Check: {
      /**
       * Category
       * @enum {string}
       */
      category: "safe_observation" | "technical" | "professional";
      /** Description */
      description: string;
    };
    /** CompatibilityRequest */
    CompatibilityRequest: {
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Part Id */
      part_id: string;
      /** Engine Code */
      engine_code?: string | null;
    };
    /** Conversation */
    Conversation: {
      /**
       * Conversation Id
       * Format: uuid
       */
      conversation_id?: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at?: string;
      /** Messages */
      messages?: components["schemas"]["Message"][];
      /** Diagnostic Ids */
      diagnostic_ids?: string[];
      /**
       * Resolution Status
       * @default active
       * @enum {string}
       */
      resolution_status: "active" | "resolved";
      /** Resolved At */
      resolved_at?: string | null;
      /** Resolution Note */
      resolution_note?: string | null;
    };
    /** ConversationCreate */
    ConversationCreate: {
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** Diagnostic */
    Diagnostic: {
      /** Summary */
      summary: string;
      urgency_level: components["schemas"]["Urgency"];
      /**
       * Driving Recommendation
       * @enum {string}
       */
      driving_recommendation:
        | "stop_safely_do_not_drive"
        | "inspection_before_driving"
        | "caution_and_monitor";
      /** Follow Up Questions */
      follow_up_questions: string[];
      /** Possible Causes */
      possible_causes: components["schemas"]["Hypothesis"][];
      /** Recommended Checks */
      recommended_checks: components["schemas"]["Check"][];
      /** Professional Assistance Recommended */
      professional_assistance_recommended: boolean;
      /** Limitations */
      limitations: string[];
      /** Next Steps */
      next_steps: string[];
      /**
       * Diagnostic Id
       * Format: uuid
       */
      diagnostic_id?: string;
      /**
       * Conversation Id
       * Format: uuid
       */
      conversation_id: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at?: string;
      /** Extracted Symptoms */
      extracted_symptoms: string[];
      /** Evidence Sources */
      evidence_sources: components["schemas"]["Evidence"][];
      /** Citations */
      citations?: components["schemas"]["SourceCitation"][];
      /**
       * Rag Available
       * @default false
       */
      rag_available: boolean;
      /**
       * Mcp Available
       * @default false
       */
      mcp_available: boolean;
      /** Tool Results */
      tool_results?: components["schemas"]["AutomotiveResult"][];
      /**
       * Generation Mode
       * @enum {string}
       */
      generation_mode: "llm" | "deterministic_safety";
      urgency_assessment?: components["schemas"]["UrgencyAssessment"] | null;
    };
    /** DiagnosticRequest */
    DiagnosticRequest: {
      /** Description */
      description: string;
      /** Symptoms */
      symptoms?: string[];
      /** Warning Lights */
      warning_lights?: string[];
      /** Dtcs */
      dtcs?: string[];
      /** Mileage Km */
      mileage_km?: number | null;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Conversation Id */
      conversation_id?: string | null;
    };
    /** Evidence */
    Evidence: {
      /**
       * Kind
       * @enum {string}
       */
      kind:
        | "user_provided"
        | "general_model_knowledge"
        | "retrieved_technical_documentation"
        | "external_tool_result";
      /** Description */
      description: string;
    };
    /** GetPartPrices */
    GetPartPrices: {
      /** Part Id */
      part_id: string;
      /**
       * Country
       * @default ES
       */
      country: string;
      /**
       * Currency
       * @default EUR
       */
      currency: string;
      /** Provider */
      provider?: string | null;
      /**
       * Quantity
       * @default 1
       */
      quantity: number;
    };
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components["schemas"]["ValidationError"][];
    };
    /** Hypothesis */
    Hypothesis: {
      /**
       * Label
       * @constant
       */
      label: "hypothesis";
      /** Component Or System */
      component_or_system: string;
      /** Possible Failure */
      possible_failure: string;
      /** Supporting Symptoms */
      supporting_symptoms: string[];
      /** Missing Or Contradictory Evidence */
      missing_or_contradictory_evidence: string[];
      /** Recommended Verification */
      recommended_verification: string;
      /** Professional Inspection Required */
      professional_inspection_required: boolean;
      /**
       * Uncertainty
       * @enum {string}
       */
      uncertainty: "possible" | "uncertain" | "insufficient_evidence";
    };
    /** Message */
    Message: {
      /**
       * Message Id
       * Format: uuid
       */
      message_id?: string;
      /**
       * Role
       * @enum {string}
       */
      role: "user" | "assistant";
      /** Content */
      content: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at?: string;
    };
    /** MessageRequest */
    MessageRequest: {
      /** Description */
      description: string;
      /** Symptoms */
      symptoms?: string[];
      /** Warning Lights */
      warning_lights?: string[];
      /** Dtcs */
      dtcs?: string[];
      /** Mileage Km */
      mileage_km?: number | null;
    };
    /** Part */
    Part: {
      /** Part Id */
      part_id: string;
      /** Name */
      name: string;
      /** Manufacturer */
      manufacturer: string;
      /** Brand */
      brand: string;
      /** Oem Reference */
      oem_reference?: string | null;
      /**
       * Oem Verified
       * @default false
       */
      oem_verified: boolean;
      /** Category */
      category: string;
      /** Description */
      description: string;
      /** Source */
      source: string;
      /** Source Url */
      source_url?: string | null;
      /**
       * Compatibility
       * @default unknown
       * @enum {string}
       */
      compatibility:
        | "confirmed_compatible"
        | "confirmed_incompatible"
        | "requires_additional_information"
        | "unknown";
      /**
       * Verification
       * @default unverified
       * @enum {string}
       */
      verification: "unverified" | "verified_provider" | "synthetic";
    };
    /** PartsSearchRequest */
    PartsSearchRequest: {
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Component */
      component: string;
      /** Oem Reference */
      oem_reference?: string | null;
      /** Manufacturer */
      manufacturer?: string | null;
      /** Category */
      category?: string | null;
      /**
       * Limit
       * @default 5
       */
      limit: number;
    };
    /** Price */
    Price: {
      /** Part Id */
      part_id: string;
      /** Merchant */
      merchant: string;
      /** Unit Price */
      unit_price: string;
      /** Currency */
      currency: string;
      /** Country */
      country: string;
      /** Quantity */
      quantity: number;
      /** Tax Included */
      tax_included?: boolean | null;
      /**
       * Availability
       * @default unknown
       * @enum {string}
       */
      availability: "in_stock" | "out_of_stock" | "unknown" | "demonstration";
      /** Product Url */
      product_url?: string | null;
      /**
       * Retrieved At
       * Format: date-time
       */
      retrieved_at?: string;
      /**
       * Verification
       * @enum {string}
       */
      verification: "live" | "historical" | "synthetic";
    };
    /** ResolveCaseRequest */
    ResolveCaseRequest: {
      /**
       * Expected Latest Diagnostic Id
       * Format: uuid
       */
      expected_latest_diagnostic_id: string;
      /** Resolution Note */
      resolution_note?: string | null;
    };
    /** SearchRequest */
    SearchRequest: {
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Query */
      query: string;
    };
    /** SourceCitation */
    SourceCitation: {
      /**
       * Document Id
       * Format: uuid
       */
      document_id: string;
      /**
       * Chunk Id
       * Format: uuid
       */
      chunk_id: string;
      /** Document Title */
      document_title: string;
      /** Publisher */
      publisher: string | null;
      /** Source Url */
      source_url: string | null;
      /** Page */
      page: number | null;
      /** Section */
      section: string | null;
      /**
       * Evidence Type
       * @enum {string}
       */
      evidence_type:
        | "official_manufacturer"
        | "third_party_technical"
        | "generic_reference"
        | "internal_demo";
      /** Verification Status */
      verification_status: string;
    };
    /** ToolResult */
    ToolResult: {
      /** Available */
      available: boolean;
      /** Reason */
      reason: string;
      /**
       * Tools
       * @default []
       */
      tools: string[];
      /**
       * Provider
       * @default unavailable
       */
      provider: string;
      /**
       * Demo Data
       * @default false
       */
      demo_data: boolean;
    };
    /**
     * Urgency
     * @enum {string}
     */
    Urgency: "low" | "moderate" | "high" | "critical";
    /** UrgencyAssessment */
    UrgencyAssessment: {
      level: components["schemas"]["Urgency"];
      /** Explanation */
      explanation: string;
      /** Warning Signs */
      warning_signs: string[];
      /** Missing Safety Information */
      missing_safety_information: string[];
      /**
       * Driving Recommendation
       * @enum {string}
       */
      driving_recommendation:
        | "stop_safely_do_not_drive"
        | "inspection_before_driving"
        | "caution_and_monitor";
      /** Professional Assistance Recommended */
      professional_assistance_recommended: boolean;
      /**
       * Basis
       * @enum {string}
       */
      basis: "deterministic_safety" | "hybrid" | "insufficient_information";
    };
    /** ValidationError */
    ValidationError: {
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
      /** Input */
      input?: unknown;
      /** Context */
      ctx?: Record<string, never>;
    };
    /** Vehicle */
    Vehicle: {
      /** Manufacturer */
      manufacturer: string;
      /** Model */
      model: string;
      /** Model Year */
      model_year: number;
      /** Engine */
      engine: string;
      /** Fuel Type */
      fuel_type: string;
      /** Transmission */
      transmission: string;
      /** Engine Code */
      engine_code?: string | null;
      /** Power Output */
      power_output?: string | null;
      /** Mileage Km */
      mileage_km?: number | null;
      /** Vin */
      vin?: string | null;
      /** Additional Information */
      additional_information?: string | null;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id?: string;
    };
    /** VehicleCreate */
    VehicleCreate: {
      /** Manufacturer */
      manufacturer: string;
      /** Model */
      model: string;
      /** Model Year */
      model_year: number;
      /** Engine */
      engine: string;
      /** Fuel Type */
      fuel_type: string;
      /** Transmission */
      transmission: string;
      /** Engine Code */
      engine_code?: string | null;
      /** Power Output */
      power_output?: string | null;
      /** Mileage Km */
      mileage_km?: number | null;
      /** Vin */
      vin?: string | null;
      /** Additional Information */
      additional_information?: string | null;
    };
    /** VehiclePatch */
    VehiclePatch: {
      /** Manufacturer */
      manufacturer?: string | null;
      /** Model */
      model?: string | null;
      /** Model Year */
      model_year?: number | null;
      /** Engine */
      engine?: string | null;
      /** Fuel Type */
      fuel_type?: string | null;
      /** Transmission */
      transmission?: string | null;
      /** Engine Code */
      engine_code?: string | null;
      /** Power Output */
      power_output?: string | null;
      /** Mileage Km */
      mileage_km?: number | null;
      /** Vin */
      vin?: string | null;
      /** Additional Information */
      additional_information?: string | null;
    };
    /** VehicleUrgency */
    VehicleUrgency: {
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      urgency_level: components["schemas"]["Urgency"] | null;
      /** Active Case Count */
      active_case_count: number;
      /** Resolved Case Count */
      resolved_case_count: number;
      /** Explanation */
      explanation: string;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  health_api_v1_health_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
    };
  };
  list_vehicles_api_v1_vehicles_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"][];
        };
      };
    };
  };
  create_vehicle_api_v1_vehicles_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VehicleCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_cases_api_v1_vehicles__vehicle_id__cases_get: {
    parameters: {
      query?: {
        resolution_status?: ("active" | "resolved") | null;
      };
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CaseSummary"][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  vehicle_urgency_api_v1_vehicles__vehicle_id__urgency_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["VehicleUrgency"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  case_history_api_v1_vehicles__vehicle_id__case_history_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CaseHistory"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_vehicle_api_v1_vehicles__vehicle_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  update_vehicle_api_v1_vehicles__vehicle_id__patch: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VehiclePatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  create_conversation_api_v1_conversations_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ConversationCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Conversation"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_conversation_api_v1_conversations__conversation_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Conversation"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  resolve_case_api_v1_conversations__conversation_id__resolve_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ResolveCaseRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CaseSummary"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  reopen_case_api_v1_conversations__conversation_id__reopen_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["CaseVersion"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CaseSummary"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  add_message_api_v1_conversations__conversation_id__messages_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["MessageRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Diagnostic"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  create_diagnostic_api_v1_diagnostics_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["DiagnosticRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Diagnostic"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_diagnostic_api_v1_diagnostics__diagnostic_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        diagnostic_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Diagnostic"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  upload_api_v1_documents_upload_post: {
    parameters: {
      query?: never;
      header?: {
        "x-admin-token"?: string | null;
      };
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "multipart/form-data": components["schemas"]["Body_upload_api_v1_documents_upload_post"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  sources_api_v1_documents_sources_get: {
    parameters: {
      query?: never;
      header?: {
        "x-admin-token"?: string | null;
      };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  documents_api_v1_documents_get: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: {
        "x-admin-token"?: string | null;
      };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  document_api_v1_documents__document_id__get: {
    parameters: {
      query?: never;
      header?: {
        "x-admin-token"?: string | null;
      };
      path: {
        document_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  delete_document_api_v1_documents__document_id__delete: {
    parameters: {
      query?: never;
      header?: {
        "x-admin-token"?: string | null;
      };
      path: {
        document_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  index_document_api_v1_documents__document_id__index_post: {
    parameters: {
      query?: never;
      header?: {
        "x-admin-token"?: string | null;
      };
      path: {
        document_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  search_api_v1_retrieval_search_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SearchRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  status_api_v1_retrieval_status_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
    };
  };
  stats_api_v1_retrieval_stats_get: {
    parameters: {
      query?: never;
      header?: {
        "x-admin-token"?: string | null;
      };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  status_api_v1_tools_status_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ToolResult"];
        };
      };
    };
  };
  search_api_v1_parts_search_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PartsSearchRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AutomotiveResult"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  compatibility_api_v1_parts_compatibility_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["CompatibilityRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AutomotiveResult"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  prices_api_v1_parts_prices_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["GetPartPrices"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AutomotiveResult"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
}
