/**
 * ProjectGen Slash Command for Continue
 * 
 * 设计两种用法：
 * /projectgen repo=<repo_name> [dataset=<dataset>] [model=<model>] 更多用于测试，可以指定数据集和仓库名
 * /projectgen project=<path> [model=<model>] 这个会递归寻找当前目录下的项目
 */

import { SlashCommand } from "../../../index.js";

// 类型定义
interface GeneratedFile {
  path: string;
  content: string;
}

interface RepoConfig {
  PRD: string;
  UML?: string[];
  architecture_design?: string;
  language?: string;
  code_file_DAG?: string[];
}

interface ProjectStatus {
  project_id: string;
  status: "pending" | "running" | "completed" | "failed";
  current_stage: string;
  iteration: number;
  progress: number;
  message?: string;
  error?: string;
  result?: {
    arch_steps?: number;
    skeleton_steps?: number;
    code_steps?: number;
  };
}

// 服务器地址（可配置）
const SERVER_URL = "http://localhost:5000";

const ProjectGenSlashCommand: SlashCommand = {
  name: "projectgen",
  description: "Generate a complete project using multi-agent workflow",
  run: async function* ({ ide, input, params, fetch, abortController }) {
    try {
      // 1. 解析用户输入
      const config = parseInput(input, params);
      
      if (!config.repo_name && !config.project_path) {
        yield "**Error**: Please specify `repo` or `project` parameter\n\n";
        yield "**Usage 1**: `/projectgen repo=<repo_name> [dataset=<dataset>] [model=<model>]`\n";
        yield "**Usage 2**: `/projectgen project=<path> [model=<model>]`\n\n";
        yield "**Example**: `/projectgen repo=bplustree dataset=CodeProjectEval model=gpt-4o`\n";
        yield "**Example**: `/projectgen project=my-project`\n";
        return;
      }

      yield "**ProjectGen - Multi-Agent Project Generation**\n\n";

      // 2. 获取工作区路径
      const workspaceDirs = await ide.getWorkspaceDirs();
      if (!workspaceDirs || workspaceDirs.length === 0) {
        yield "**Error**: No workspace folder opened\n";
        return;
      }
      const workspaceDir = workspaceDirs[0];

      // 3. 如果使用 project 参数，递归查找项目
      let projectDir: string;
      let actualRepoName: string;
      let actualDataset: string;

      if (config.project_path) {
        yield "Searching for projects...\n";
        const searchRoot = `${workspaceDir}/${config.project_path}`;
        const foundProjects = await findProjects(searchRoot, ide);
        
        if (foundProjects.length === 0) {
          yield `**Error**: No valid projects found in \`${config.project_path}\`\n`;
          yield "A valid project must contain:\n";
          yield "- config.json\n";
          yield "- PRD file (specified in config.json)\n";
          return;
        }
        
        if (foundProjects.length > 1) {
          yield `Found ${foundProjects.length} projects:\n\n`;
          for (let i = 0; i < foundProjects.length; i++) {
            yield `${i + 1}. \`${foundProjects[i].relativePath}\`\n`;
          }
          yield "\nMultiple projects found. Please specify one using \`repo=\` parameter\n";
          return;
        }
        
        projectDir = foundProjects[0].fullPath;
        actualRepoName = foundProjects[0].name;
        actualDataset = foundProjects[0].dataset;
        yield `Found project: \`${foundProjects[0].relativePath}\`\n\n`;
      } else {
        projectDir = `${workspaceDir}/datasets/${config.dataset}/${config.repo_name}`;
        actualRepoName = config.repo_name;
        actualDataset = config.dataset;
      }

      yield "**Configuration**:\n";
      yield `- Repository: \`${actualRepoName}\`\n`;
      yield `- Dataset: \`${actualDataset}\`\n`;
      yield `- Model: \`${config.model}\`\n\n`;

      // 4. 读取项目配置文件 (config.json)
      yield "Reading project configuration...\n";
      const configPath = `${projectDir}/config.json`;
      
      let repoConfig: RepoConfig;
      try {
        const configContent = await ide.readFile(configPath);
        repoConfig = JSON.parse(configContent);
      } catch (error: any) {
        yield `**Error**: Cannot read config.json from \`${configPath}\`\n`;
        yield `Details: ${error.message}\n`;
        return;
      }

      // 5. 读取 PRD 文件（根据 config.json 中的路径）
      yield "Reading PRD...\n";
      const prdPath = `${projectDir}/${repoConfig.PRD}`;
      
      let requirement: string;
      try {
        requirement = await ide.readFile(prdPath);
        yield `PRD loaded (${requirement.length} chars)\n`;
      } catch (error: any) {
        yield `**Error**: Cannot read PRD file from \`${prdPath}\`\n`;
        yield `Details: ${error.message}\n`;
        return;
      }

      // 6. 读取架构设计文件（如果存在）
      let archDesign = "";
      if (repoConfig.architecture_design) {
        try {
          const archPath = `${projectDir}/${repoConfig.architecture_design}`;
          archDesign = await ide.readFile(archPath);
          yield `Architecture design loaded\n`;
        } catch (error) {
          // 架构设计文件是可选的
        }
      }

      // 7. 读取 UML 文件（如果存在）
      let umlClass = "";
      let umlSequence = "";
      if (repoConfig.UML && repoConfig.UML.length > 0) {
        try {
          // 读取第一个 UML 文件作为类图
          const umlPath = `${projectDir}/${repoConfig.UML[0]}`;
          umlClass = await ide.readFile(umlPath);
          yield `UML loaded (${repoConfig.UML[0]})\n`;
          
          // 如果有第二个 UML 文件，作为时序图
          if (repoConfig.UML.length > 1) {
            const umlSeqPath = `${projectDir}/${repoConfig.UML[1]}`;
            umlSequence = await ide.readFile(umlSeqPath);
            yield `UML sequence loaded (${repoConfig.UML[1]})\n`;
          }
        } catch (error) {
          // UML 文件是可选的
        }
      }

      // 8. 连接服务器
      yield "\nConnecting to ProjectGen server...\n";
      try {
        const healthResponse = await fetch(`${SERVER_URL}/api/health`, {
          signal: abortController.signal
        });
        const healthData = await healthResponse.json();
        yield `Server connected (${healthData.active_tasks} active tasks)\n\n`;
      } catch (error: any) {
        yield `**Error**: Cannot connect to server at ${SERVER_URL}\n`;
        yield `Details: ${error.message}\n`;
        yield `\n**Hint**: Please start the server first:\n`;
        yield `\`\`\`bash\ncd projectgen-server\npython main.py\n\`\`\`\n`;
        return;
      }

      // 9. 启动生成任务
      yield "Starting generation task...\n";
      let projectId: string;
      try {
        const generateResponse = await fetch(`${SERVER_URL}/api/projects/generate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            dataset: actualDataset,
            repo_name: actualRepoName,
            requirement: requirement,
            uml_class: umlClass,
            uml_sequence: umlSequence,
            arch_design: archDesign,
            model: config.model,
            code_file_DAG: repoConfig.code_file_DAG || []
          }),
          signal: abortController.signal
        });

        if (!generateResponse.ok) {
          const errorData = await generateResponse.json();
          yield `**Error**: ${errorData.detail || 'Failed to start generation'}\n`;
          return;
        }

        const generateData = await generateResponse.json();
        projectId = generateData.project_id;
        yield `Project ID: \`${projectId}\`\n\n`;
      } catch (error: any) {
        if (error.name === 'AbortError') {
          yield "\nGeneration cancelled by user\n";
          return;
        }
        yield `**Error**: ${error.message}\n`;
        return;
      }

      // 10. 显示工作流程图
      yield "**Workflow**:\n";
      yield "```\n";
      yield "┌──────────────┐     ┌──────────────┐     ┌──────────────┐\n";
      yield "│Architecture │ ──> │  Skeleton    │ ──> │    Code      │\n";
      yield "│   Design     │     │ Generation   │     │ Filling      │\n";
      yield "└──────────────┘     └──────────────┘     └──────────────┘\n";
      yield "```\n\n";

      // 11. 轮询进度
      yield "**Progress**:\n\n";
      
      let isComplete = false;
      let lastStage = "";
      let lastIteration = 0;

      while (!isComplete) {
        // 检查是否被用户取消
        if (abortController.signal.aborted) {
          yield "\nGeneration cancelled by user\n";
          break;
        }

        // 等待3秒
        await sleep(3000);

        try {
          const statusResponse = await fetch(
            `${SERVER_URL}/api/projects/${projectId}/status`,
            { signal: abortController.signal }
          );
          const statusData: ProjectStatus = await statusResponse.json();

          // 如果阶段或迭代改变，显示新的进度
          if (statusData.current_stage !== lastStage || statusData.iteration !== lastIteration) {
            const stageName = formatStageName(statusData.current_stage);
            yield `**${stageName}**\n`;
            yield `  - Iteration ${statusData.iteration}\n`;
            lastStage = statusData.current_stage;
            lastIteration = statusData.iteration;
          }

          // 显示进度条
          const progressBar = generateProgressBar(statusData.progress);
          yield `${progressBar} ${statusData.progress}%\n`;

          // 检查是否完成
          if (statusData.status === "completed") {
            isComplete = true;
            yield `\n**Generation Completed!**\n\n`;
            
            if (statusData.result) {
              yield "**Statistics**:\n";
              yield `- Architecture iterations: ${statusData.result.arch_steps || 0}\n`;
              yield `- Skeleton iterations: ${statusData.result.skeleton_steps || 0}\n`;
              yield `- Code iterations: ${statusData.result.code_steps || 0}\n\n`;
            }
          } else if (statusData.status === "failed") {
            yield `\n**Error**: ${statusData.error || 'Unknown error'}\n`;
            return;
          }
        } catch (error: any) {
          if (error.name === 'AbortError') {
            yield "\nGeneration cancelled by user\n";
            break;
          }
          yield `\n**Warning**: Status check failed: ${error.message}\n`;
        }
      }

      if (!isComplete) {
        return;
      }

      // 12. 获取生成的文件
      yield "Retrieving generated files...\n";
      let files: GeneratedFile[] = [];
      try {
        const filesResponse = await fetch(
          `${SERVER_URL}/api/projects/${projectId}/files`
        );
        const filesData = await filesResponse.json();
        files = filesData.files;
        yield `Retrieved ${files.length} files\n\n`;
      } catch (error: any) {
        yield `**Error**: Failed to retrieve files: ${error.message}\n`;
        return;
      }

      // 13. 写入文件到工作区
      if (files.length > 0) {
        yield "Writing files to workspace...\n";
        const outputDir = `${workspaceDir}/${actualDataset}_outputs/${actualRepoName}`;
        
        for (const file of files) {
          try {
            const fullPath = `${outputDir}/${file.path}`;
            await ide.writeFile(fullPath, file.content);
            yield `  [OK] ${file.path}\n`;
          } catch (error: any) {
            yield `  [Failed] ${file.path} (${error.message})\n`;
          }
        }

        yield `\nOutput directory: \`${actualDataset}_outputs/${actualRepoName}\`\n`;
      } else {
        yield "No files generated\n";
      }

      yield "\n**Done!**\n";
      
    } catch (error: any) {
      yield `\n**Unexpected Error**: ${error.message}\n`;
      console.error("ProjectGen error:", error);
    }
  }
};

// 辅助函数
function parseInput(input: string, params: any): { dataset: string; repo_name: string; model: string; project_path: string } {
  const config = {
    dataset: params?.dataset || "CodeProjectEval",
    repo_name: "",
    model: params?.model || "gpt-4o",
    project_path: ""
  };
  
  // 从输入字符串解析参数
  const repoMatch = input.match(/repo=(\S+)/);
  if (repoMatch) config.repo_name = repoMatch[1];
  
  const datasetMatch = input.match(/dataset=(\S+)/);
  if (datasetMatch) config.dataset = datasetMatch[1];
  
  const modelMatch = input.match(/model=(\S+)/);
  if (modelMatch) config.model = modelMatch[1];
  
  const projectMatch = input.match(/project=(\S+)/);
  if (projectMatch) config.project_path = projectMatch[1];
  
  return config;
}

function formatStageName(stage: string): string {
  const map: Record<string, string> = {
    "architecture": "Architecture Design",
    "skeleton": "Skeleton Generation",
    "code": "Code Implementation"
  };
  return map[stage] || stage;
}

function generateProgressBar(progress: number, width: number = 20): string {
  const filled = Math.floor((progress / 100) * width);
  const empty = width - filled;
  return `[${"█".repeat(filled)}${"░".repeat(empty)}]`;
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// 递归查找包含必需文件的项目目录
async function findProjects(rootPath: string, ide: any): Promise<Array<{fullPath: string; relativePath: string; name: string; dataset: string}>> {
  const projects: Array<{fullPath: string; relativePath: string; name: string; dataset: string}> = [];
  
  async function searchDir(dirPath: string, relativePath: string = "") {
    try {
      const entries = await ide.listDir(dirPath);
      
      // 检查当前目录是否包含 config.json
      const hasConfig = entries.some((e: string) => e === "config.json" || e === "config.json/");
      
      if (hasConfig) {
        // 验证是否包含必需文件
        try {
          const configContent = await ide.readFile(`${dirPath}/config.json`);
          const config = JSON.parse(configContent);
          
          // 检查 PRD 文件是否存在
          if (config.PRD) {
            try {
              await ide.readFile(`${dirPath}/${config.PRD}`);
              
              // 推断 dataset 和 name
              const parts = relativePath.split("/").filter(p => p);
              let dataset = "Unknown";
              let name = parts[parts.length - 1] || "unknown";
              
              // 尝试从路径推断 dataset (如果路径包含 datasets/XXX/repo)
              const datasetIdx = parts.indexOf("datasets");
              if (datasetIdx >= 0 && parts.length > datasetIdx + 1) {
                dataset = parts[datasetIdx + 1];
                if (parts.length > datasetIdx + 2) {
                  name = parts[datasetIdx + 2];
                }
              }
              
              projects.push({
                fullPath: dirPath,
                relativePath: relativePath || ".",
                name: name,
                dataset: dataset
              });
            } catch {
              // PRD 文件不存在，跳过
            }
          }
        } catch {
          // config.json 格式错误，跳过
        }
      }
      
      // 递归搜索子目录
      for (const entry of entries) {
        if (entry.endsWith("/")) {
          const subDirName = entry.slice(0, -1);
          // 跳过一些常见的无关目录
          if (["node_modules", ".git", "__pycache__", "dist", "build", ".vscode"].includes(subDirName)) {
            continue;
          }
          const subPath = `${dirPath}/${subDirName}`;
          const subRelative = relativePath ? `${relativePath}/${subDirName}` : subDirName;
          await searchDir(subPath, subRelative);
        }
      }
    } catch (error) {
      // 目录读取失败，跳过
    }
  }
  
  await searchDir(rootPath);
  return projects;
}

export default ProjectGenSlashCommand;
