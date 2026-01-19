import json

SSAT_JSON_SCHEMA = {
  "title": "SemanticSoftwareArchitectureTree",
  "type": "object",
  "properties": {
    "modules": {
      "type": "array",
      "description": "A list of modules representing the SSAT.",
      "items": { "$ref": "#/$defs/Module" }
    }
  },
  "required": ["modules"],

  "$defs": {
    "Module": {
      "type": "object",
      "description": "A top-level module in the SSAT.",
      "properties": {
        "name": { "type": "string" },
        "description": { "type": "string" },
        "files": {
          "type": "array",
          "items": { "$ref": "#/$defs/File" }
        }
      },
      "required": ["name", "description", "files"]
    },

    "File": {
      "type": "object",
      "description": "A file within a module.",
      "properties": {
        "name": { "type": "string" },
        "path": { "type": "string" },
        "description": { "type": "string" },
        "global_code": {
          "type": "object",
          "description": "Top-level statements, global variables, or initialization code within a file.",
          "properties": {
              "globalVariables": {
              "type": "array",
              "description": "Top-level global variable declarations.",
              "items": { "$ref": "#/$defs/GlobalVariable" }
            },
            "globalBlocks": {
              "type": "array",
              "description": "Top-level initialization code blocks or statements.",
              "items": { "$ref": "#/$defs/GlobalBlock" }
            }
          }
        },
        "classes": {
          "type": "array",
          "description": "Classes defined in this file.",
          "items": { "$ref": "#/$defs/Class" }
        },
        "functions": {
          "type": "array",
          "description": "Global-level functions defined in this file.",
          "items": { "$ref": "#/$defs/Function" }
        }
      },
      "required": ["name", "path", "description"]
    },

# 更新：区别global变量和global代码块
    "GlobalVariable": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "type": { "type": "string" },
        "description": { "type": "string" }
      },
      "required": ["name", "type", "description"]
    },

    "GlobalBlock": {
      "type": "object",
      "properties": {
        "description": { "type": "string" },
      },
      "required": ["description"]
    },

# 更新：增加class的成员变量
    "Class": {
      "type": "object",
      "description": "A class defined inside a file.",
      "properties": {
        "name": { "type": "string" },
        "description": { "type": "string" },
        "attributes": {
          "type": "array",
          "description": "Member variables of the class.",
          "items": { "$ref": "#/$defs/ClassAttribute" }
        },
        "methods": {
          "type": "array",
          "description": "Member methods of the class.",
          "items": { "$ref": "#/$defs/Function" }
        }
      },
      "required": ["name", "description"]
    },

    "ClassAttribute": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "type": { "type": "string" },
        "description": { "type": "string" }
      },
      "required": ["name", "type"]
    },

    "Function": {
      "type": "object",
      "description": "A function or method.",
      "properties": {
        "name": { "type": "string" },
        "description": { "type": "string" },
        "parameters": {
          "type": "array",
          "items": { "$ref": "#/$defs/Parameter" }
        },
        "return_type": { "type": "string" }
      },
      "required": ["name", "description", "parameters", "return_type"]
    },

    "Parameter": {
      "type": "object",
      "description": "A function parameter.",
      "properties": {
        "name": { "type": "string" },
        "type": { "type": "string" },
        "description": { "type": "string" }
      },
      "required": ["name", "type"]
    }


  }
}

ARCH_JUDGE_JSON_SCHEMA = {
  "title": "ArchitectureJudgeSchema",
  "type": "object",
  "description": "Schema for evaluating software architecture.",
  "properties": {
    "feedback": {
      "type": "object",
      "description": "Detailed feedback on various evaluation criteria.",
      "properties": {
        "requirement_coverage": { 
          "type": "object",
          "properties": {
            "score": { "type": "number", "minimum": 1, "maximum": 10 },
            "comments": { "type": "string" }
          },
          "required": ["score", "comments"]
        },
        "consistency_with_provided_information": { 
          "type": "object",
          "properties": {
            "score": { "type": "number", "minimum": 1, "maximum": 10 },
            "comments": { "type": "string" }
          },
          "required": ["score", "comments"]
        },
        "interface_consistency": { 
          "type": "object",
          "properties": {
            "score": { "type": "number", "minimum": 1, "maximum": 10 },
            "comments": { "type": "string" }
          },
          "required": ["score", "comments"]
        },
        "dependency_relations": { 
          "type": "object",
          "properties": {
            "score": { "type": "number", "minimum": 1, "maximum": 10 },
            "comments": { "type": "string" }
          },
          "required": ["score", "comments"]
        },
      },
      "required": ["requirement_coverage", "consistency_with_provided_information", "interface_consistency", "dependency_relations"]
    },
    "final_score": {
      "type": "number",
      "description": "Overall score for the architecture evaluation.",
      "minimum": 1,
      "maximum": 10
    }
  },
  "required": ["feedback", "final_score"],
}

SKELETON_JSON_SCHEMA = {
  "title": "SkeletonCodeSchema",
  "type": "object",
  "description": "Schema for the generated skeleton code for a file.",
  "properties": {
      "path": { 
        "type": "string",
        "description": "The file path of the code file."
      },
      "skeleton_code": {
        "type": "string",
        "description": "The skeleton code for the file, with function bodies replaced with `pass`."
      }
    },
  "required": ["path", "skeleton_code"]
}

SKELETON_JUDGE_SCHEMA = {
  "title": "SkeletonJudgeSchema",
  "type": "object",
  "description": "Schema for evaluating skeleton of code files.",
  "properties": {
    "feedback": {
      "type": "object",
      "description": "Detailed feedback on various evaluation criteria.",
      "properties": {
        "directory_structure_matching": { 
          "type": "object",
          "properties": {
            "score": { "type": "number", "minimum": 1, "maximum": 10 },
            "comments": { "type": "string" }
          },
          "required": ["score", "comments"]
        },
        "interface_and_call_relationship_matching": { 
          "type": "object",
          "properties": {
            "score": { "type": "number", "minimum": 1, "maximum": 10 },
            "comments": { "type": "string" }
          },
          "required": ["score", "comments"]
        },
      },
      "required": ["directory_structure_matching", "interface_and_call_relationship_matching"]
    },
    "final_score": {
      "type": "number",
      "description": "Overall score for the skeleton evaluation.",
      "minimum": 1,
      "maximum": 10
    }
  },
  "required": ["feedback", "final_score"],
}

CODE_JSON_SCHEMA = {
  "title": "CodeSchema",
  "type": "object",
  "description": "Schema for the generated complete code for a file.",
  "properties": {
      "path": { 
        "type": "string",
        "description": "The file path of the code file."
      },
      "code": {
        "type": "string",
        "description": "The complete code for the file."
      }
    },
  "required": ["path", "code"]
}

CODE_JUDGE_SCHEMA = {
  "title": "CodeJudgeSchema",
  "type": "object",
  "description": "Schema for evaluating the code files.",
  "properties": {
    "feedback":{
      "type": "array",
      "description": "A list of feedback items for the code evaluation.",
      "items": { "$ref": "#/$defs/FeedbackItem" }
    }
  },
  "required": ["feedback"],

  "$defs": {
    "FeedbackItem": {
      "type": "object",
      "description": "Feedback for a specific issue found in the code.",
      "properties": {
        "summary": {
          "type": "string",
          "description": "A clear and concise summary of the issue found in the code.",
        },
        "likely_cause": {
          "type": "string",
          "description": "The most likely root cause of the issue found in the code."
        },
        "suggested_fix": {
          "type": "string",
          "description": "The actionable modification suggestions to fix the issue."
        }
      },
      "required": ["summary", "likely_cause", "suggested_fix"]
    }
  }
}

CODE_FILE_UPDATE_SCHEMA = {
  "title": "CodeFileUpdateSchema",
  "type": "object",
  "description": "Schema for code files to be updated.",
  "properties": {
    "files_to_update": {
      "type": "array",
      "description": "The paths of the code files to be updated.",
      "items": { 
        "type": "string",
        "description": "The file path of the code file to be updated."
      }
    },
  },
  "required": ["files_to_update"]
}

EXPERIENCE_JSON_SCHEMA = {
  "title": "ExperienceSummarySchema",
  "type": "object",
  "properties": {
    "experiences": {
      "type": "array",
      "description": "A list of summarized coding experiences extracted from the interaction.",
      "items": { "$ref": "#/$defs/Experience" }
    }
  },
  "required": ["experiences"],

  "$defs": {
    "Experience": {
      "type": "object",
      "properties": {
        "kind": {
          "type": "string",
          "description": "The kind of experience.",
          "enum": ["success", "failure"]
        },
        "scenario": {
          "type": "string",
          "description": "A short description of the error or success scenario."
        },
        "experience": {
          "type": "string",
          "description": "The summarized coding experience."
        }
      },
      "required": ["name", "description", "files"]
    }
  }
}
