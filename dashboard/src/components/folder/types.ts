/**
 * 通用文件夹管理组件类型定义
 *
 * 这是一个可复用的文件夹管理系统，可用于管理各种类型的项目（如 prompt、模板、知识库等）
 */

/**
 * 文件夹基础接口
 */
export interface Folder {
  folder_id: string;
  name: string;
  parent_id: string | null;
  description?: string | null;
  sort_order?: number;
  created_at?: string;
  updated_at?: string;
}

/**
 * 文件夹树节点接口
 */
export interface FolderTreeNode extends Folder {
  children: FolderTreeNode[];
}

/**
 * 拖拽放置事件数据
 */
export interface DropEventData {
  item_id: string;
  item_type: string;
  target_folder_id: string | null;
  source_data?: unknown;
}

/**
 * 文件夹操作接口 - 由使用方提供具体实现
 */
export interface FolderOperations {
  // 加载文件夹树
  loadFolderTree: () => Promise<FolderTreeNode[]>;

  // 加载指定文件夹的子文件夹
  loadSubFolders: (parentId: string | null) => Promise<Folder[]>;

  // 创建文件夹
  createFolder: (data: CreateFolderData) => Promise<Folder>;

  // 更新文件夹
  updateFolder: (data: UpdateFolderData) => Promise<void>;

  // 删除文件夹
  deleteFolder: (folderId: string) => Promise<void>;

  // 移动文件夹
  moveFolder?: (
    folderId: string,
    targetParentId: string | null,
  ) => Promise<void>;
}

/**
 * 创建文件夹数据
 */
export interface CreateFolderData {
  name: string;
  parent_id?: string | null;
  description?: string;
}

/**
 * 更新文件夹数据
 */
export interface UpdateFolderData {
  folder_id: string;
  name?: string;
  description?: string;
  parent_id?: string | null;
}

/**
 * 面包屑项接口
 */
export interface BreadcrumbItem {
  title: string;
  folderId: string | null;
  disabled: boolean;
  isRoot: boolean;
}

/**
 * 上下文菜单事件
 */
export interface ContextMenuEvent {
  event: MouseEvent;
  folder: Folder;
}

/**
 * 可选择的项目基础接口
 */
export interface SelectableItem {
  id: string;
  name: string;
  description?: string | null;
  folder_id?: string | null;
  [key: string]: unknown;
}

/**
 * 文件夹项目选择器标签配置
 */
export interface FolderItemSelectorLabels {
  // 对话框
  dialogTitle?: string;
  notSelected?: string;
  buttonText?: string;

  // 项目列表
  noItems?: string;
  defaultItem?: string;
  noDescription?: string;
  emptyFolder?: string;

  // 按钮
  createButton?: string;
  editButton?: string;
  confirmButton?: string;
  cancelButton?: string;

  // 文件夹
  rootFolder?: string;
}
