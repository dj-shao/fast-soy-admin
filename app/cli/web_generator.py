"""前端代码生成器 — service / typings / views / i18n。"""

from __future__ import annotations

import re
from pathlib import Path

from app.cli.parser import FieldInfo, ModelInfo, RelationInfo

# ─── 命名转换 ───


def snake_to_camel(s: str) -> str:
    """snake_case → camelCase"""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def snake_to_pascal(s: str) -> str:
    """snake_case → PascalCase"""
    return "".join(p.title() for p in s.split("_"))


def cn_title(description: str, fallback: str) -> str:
    """从 description 中提取中文标题：截断到第一个句号前。"""
    if not description:
        return fallback
    text = description
    for sep in ("。", "."):
        if sep in text:
            text = text.split(sep)[0]
    return text.strip() or fallback


def en_title(field_name: str) -> str:
    """英文标题：snake_case → camelCase"""
    return snake_to_camel(field_name)


# ─── 字段 → TS 类型 / 表单组件 映射 ───


def field_ts_type(f: FieldInfo) -> str:
    """返回 TS 类型字符串。"""
    mapping = {
        "CharField": "string",
        "TextField": "string",
        "UUIDField": "string",
        "IntField": "number",
        "BigIntField": "number",
        "SmallIntField": "number",
        "BooleanField": "boolean",
        "DecimalField": "number",
        "FloatField": "number",
        "DatetimeField": "string",
        "DateField": "string",
        "TimeField": "string",
        "JSONField": "Record<string, any>",
        "CharEnumField": "string",
        "IntEnumField": "number",
    }
    return mapping.get(f.field_type, "string")


def field_form_component(f: FieldInfo) -> str:
    """返回表单组件类型标识: input / textarea / int / decimal / switch / date / datetime / select-status / select-todo。"""
    if f.field_type == "TextField":
        return "textarea"
    if f.field_type in ("CharField",):
        return "input"
    if f.field_type in ("IntField", "BigIntField", "SmallIntField"):
        return "int"
    if f.field_type in ("DecimalField", "FloatField"):
        return "decimal"
    if f.field_type == "BooleanField":
        return "switch"
    if f.field_type == "DateField":
        return "date"
    if f.field_type == "TimeField":
        return "time"
    if f.field_type == "DatetimeField":
        return "datetime"
    if f.field_type == "CharEnumField" and f.enum_type == "StatusType":
        return "select-status"
    if f.field_type in ("CharEnumField", "IntEnumField"):
        return "select-todo"
    return "input"


# ─── 生成 service ts ───


def gen_service_ts(module: str, models: list[ModelInfo]) -> str:
    ns = snake_to_pascal(module) + "Manage"
    lines = [
        "import { request } from '../request';",
        "",
    ]
    for model in models:
        entity = model.name  # PascalCase
        entity_snake = model.snake_name
        entity_plural = model.plural_snake
        url_base = f"/business/{module}/{entity_plural}"

        lines.extend([
            f"// ---- {entity} ----",
            f"export function fetchGet{entity}List(data?: Api.{ns}.{entity}SearchParams) {{",
            f"  return request<Api.{ns}.{entity}List>({{",
            f"    url: '{url_base}/search',",
            "    method: 'post',",
            "    data: data ?? {}",
            "  });",
            "}",
            "",
            f"export function fetchGet{entity}(id: string) {{",
            f"  return request<Api.{ns}.{entity}>({{",
            f"    url: `{url_base}/${{id}}`,",
            "    method: 'get'",
            "  });",
            "}",
            "",
            f"export function fetchAdd{entity}(data?: Api.{ns}.{entity}AddParams) {{",
            "  return request<null, 'json'>({",
            f"    url: '{url_base}',",
            "    method: 'post',",
            "    data",
            "  });",
            "}",
            "",
            f"export function fetchUpdate{entity}(data?: Api.{ns}.{entity}UpdateParams) {{",
            "  return request<null, 'json'>({",
            f"    url: `{url_base}/${{data?.id}}`,",
            "    method: 'patch',",
            "    data",
            "  });",
            "}",
            "",
            f"export function fetchDelete{entity}(data?: Api.{ns}.CommonDeleteParams) {{",
            "  return request<null>({",
            f"    url: `{url_base}/${{data?.id}}`,",
            "    method: 'delete'",
            "  });",
            "}",
            "",
            f"export function fetchBatchDelete{entity}(data?: Api.{ns}.CommonBatchDeleteParams) {{",
            "  return request<null>({",
            f"    url: '{url_base}',",
            "    method: 'delete',",
            "    data",
            "  });",
            "}",
            "",
            "",
            f"void {entity_snake};",  # placeholder to avoid unused var warning; removed below
        ])

    # 移除占位符
    lines = [line for line in lines if not line.startswith("void ")]
    return "\n".join(lines) + "\n"


# ─── 生成 typings d.ts ───


def _ts_field_line(name: str, ts_type: str, optional: bool = False, nullable: bool = False) -> str:
    """生成单行 TS 字段声明。"""
    opt = "?" if optional else ""
    nul = " | null" if nullable else ""
    return f"      {name}{opt}: {ts_type}{nul};"


def gen_typings_dts(module: str, models: list[ModelInfo], search_fields_map: dict[str, list[str]]) -> str:
    ns = snake_to_pascal(module) + "Manage"
    lines = [
        "declare namespace Api {",
        f"  namespace {ns} {{",
        "    type CommonDeleteParams = { id: string };",
        "    type CommonBatchDeleteParams = { ids: string[] };",
        "    type CommonSearchParams = Pick<Common.PaginatingCommonParams, 'current' | 'size'>;",
        "",
    ]

    for model in models:
        entity = model.name
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"    // ---- {entity} ----")

        # ---- Entity ----
        lines.append(f"    type {entity} = Common.CommonRecord<{{")
        for f in fields:
            camel = snake_to_camel(f.name)
            lines.append(_ts_field_line(camel, field_ts_type(f), optional=False, nullable=not f.required))
        for r in fk_relations:
            camel = snake_to_camel(r.name) + "Id"
            lines.append(_ts_field_line(camel, "string", optional=False, nullable=r.nullable))
        lines.append("    }>;")
        lines.append("")

        # ---- AddParams ----
        lines.append(f"    type {entity}AddParams = {{")
        for f in fields:
            camel = snake_to_camel(f.name)
            lines.append(_ts_field_line(camel, field_ts_type(f), optional=not f.required, nullable=not f.required))
        for r in fk_relations:
            camel = snake_to_camel(r.name) + "Id"
            lines.append(_ts_field_line(camel, "string", optional=r.nullable, nullable=r.nullable))
        lines.append("    };")
        lines.append("")

        # ---- UpdateParams ----
        lines.append(f"    type {entity}UpdateParams = {{ id?: string }} & Partial<{entity}AddParams>;")
        lines.append("")

        # ---- SearchParams ----
        search_names = search_fields_map.get(model.name, [])
        # 搜索参数始终加上 status (如果有)
        has_status_enum = any(f.name == "status" and f.enum_type for f in fields)

        lines.append(f"    type {entity}SearchParams = CommonType.RecordNullable<")
        lines.append("      {")
        for name in search_names:
            f = next((x for x in fields if x.name == name), None)
            if f:
                camel = snake_to_camel(name)
                lines.append(f"        {camel}?: {field_ts_type(f)};")
        if has_status_enum and "status" not in search_names:
            lines.append("        status?: string;")
        lines.append("      } & CommonSearchParams")
        lines.append("    >;")
        lines.append("")

        # ---- List ----
        lines.append(f"    type {entity}List = Common.PaginatingQueryRecord<{entity}>;")
        lines.append("")

    lines.extend([
        "  }",
        "}",
        "",
    ])
    return "\n".join(lines)


# ─── 生成 Vue views ───


def _form_item_block(
    f: FieldInfo | RelationInfo,
    i18n_page: str,
    *,
    is_relation: bool = False,
) -> list[str]:
    """为单个字段生成 <NFormItem> 块（用于 operate-drawer）。"""
    if is_relation:
        name_camel = snake_to_camel(f.name) + "Id"  # type: ignore[attr-defined]
        label_key = f"{i18n_page}.{snake_to_camel(f.name)}"  # type: ignore[attr-defined]
        placeholder_key = f"{i18n_page}.form.{snake_to_camel(f.name)}"  # type: ignore[attr-defined]
        return [
            f'      <NFormItem :label="$t(\'{label_key}\')" path="{name_camel}">',
            "        <NSelect",
            f'          v-model:value="model.{name_camel}"',
            '          :options="[]"',  # TODO
            "          clearable",
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            "        />",
            f"        <!-- TODO: 配置 {name_camel} 的 options 数据源 -->",
            "      </NFormItem>",
        ]

    assert isinstance(f, FieldInfo)
    name_camel = snake_to_camel(f.name)
    label_key = f"{i18n_page}.{name_camel}"
    placeholder_key = f"{i18n_page}.form.{name_camel}"
    component = field_form_component(f)

    base = f'      <NFormItem :label="$t(\'{label_key}\')" path="{name_camel}">'
    end = "      </NFormItem>"

    body: list[str]
    if component == "input":
        body = [f'        <NInput v-model:value="model.{name_camel}" :placeholder="$t(\'{placeholder_key}\')" />']
    elif component == "textarea":
        body = [f'        <NInput v-model:value="model.{name_camel}" type="textarea" :placeholder="$t(\'{placeholder_key}\')" />']
    elif component == "int":
        body = [f'        <NInputNumber v-model:value="model.{name_camel}" :placeholder="$t(\'{placeholder_key}\')" class="w-full" />']
    elif component == "decimal":
        precision = 2
        body = [f'        <NInputNumber v-model:value="model.{name_camel}" :precision="{precision}" :placeholder="$t(\'{placeholder_key}\')" class="w-full" />']
    elif component == "switch":
        body = [f'        <NSwitch v-model:value="model.{name_camel}" />']
    elif component in ("date", "datetime"):
        body = [f'        <NDatePicker v-model:value="model.{name_camel}" type="{component}" clearable class="w-full" />']
    elif component == "time":
        body = [f'        <NTimePicker v-model:value="model.{name_camel}" clearable class="w-full" />']
    elif component == "select-status":
        body = [
            "        <NSelect",
            f'          v-model:value="model.{name_camel}"',
            '          :options="statusTypeOptions"',
            "          clearable",
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            "        />",
        ]
    elif component == "select-todo":
        body = [
            "        <NSelect",
            f'          v-model:value="model.{name_camel}"',
            '          :options="[]"',
            "          clearable",
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            "        />",
            f"        <!-- TODO: 配置 {name_camel} 的 options 数据源 -->",
        ]
    else:
        body = [f'        <NInput v-model:value="model.{name_camel}" :placeholder="$t(\'{placeholder_key}\')" />']

    return [base, *body, end]


def _default_value_for_field(f: FieldInfo) -> str:
    """用于 createDefaultModel() 的字段默认值。"""
    if f.field_type in ("CharField", "TextField", "UUIDField", "DatetimeField", "DateField", "TimeField"):
        return "''"
    if f.field_type in ("IntField", "BigIntField", "SmallIntField", "DecimalField", "FloatField"):
        return "null"
    if f.field_type == "BooleanField":
        return "false"
    if f.field_type == "CharEnumField":
        return "''"
    return "null"


def gen_view_index(module: str, model: ModelInfo, list_fields: list[str]) -> str:
    """生成 views/<module>/<entity>/index.vue"""
    entity = model.name
    entity_snake = model.snake_name
    entity_kebab = entity_snake.replace("_", "-")
    ns = snake_to_pascal(module) + "Manage"
    i18n_page = f"page.{module}.{entity_snake}"

    fields = model.schema_fields
    fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

    # 列定义
    col_lines = [
        "    { type: 'selection', align: 'center', width: 48 },",
        "    { key: 'index', title: $t('common.index'), width: 64, align: 'center', render: (_, index) => index + 1 },",
    ]
    for name in list_fields:
        f = next((x for x in fields if x.name == name), None)
        if not f:
            # 可能是外键
            r = next((x for x in fk_relations if x.name == name), None)
            if r:
                camel = snake_to_camel(r.name) + "Id"
                col_lines.append(f"    {{ key: '{camel}', title: $t('{i18n_page}.{snake_to_camel(r.name)}'), align: 'center', minWidth: 120 }},")
            continue
        camel = snake_to_camel(f.name)
        col_lines.append(f"    {{ key: '{camel}', title: $t('{i18n_page}.{camel}'), align: 'center', minWidth: 120 }},")

    # 搜索参数字段（给 reactive 的默认值）
    search_param_lines = ["  current: 1,", "  size: 10,"]
    # 搜索参数不在这里定义，只定义 list 列；search 字段在 search.vue 里

    template = f"""<script setup lang="tsx">
import {{ reactive }} from 'vue';
import {{ NButton, NPopconfirm }} from 'naive-ui';
import {{ fetchBatchDelete{entity}, fetchDelete{entity}, fetchGet{entity}List }} from '@/service/api';
import {{ useAppStore }} from '@/store/modules/app';
import {{ defaultTransform, useNaivePaginatedTable, useTableOperate }} from '@/hooks/common/table';
import {{ $t }} from '@/locales';
import {entity}OperateDrawer from './modules/{entity_kebab}-operate-drawer.vue';
import {entity}Search from './modules/{entity_kebab}-search.vue';

const appStore = useAppStore();

const searchParams: Api.{ns}.{entity}SearchParams = reactive({{
  current: 1,
  size: 10
}});

const {{ columns, columnChecks, data, loading, getData, getDataByPage, mobilePagination }} = useNaivePaginatedTable({{
  api: () => fetchGet{entity}List(searchParams),
  transform: response => defaultTransform(response),
  onPaginationParamsChange: params => {{
    searchParams.current = params.page;
    searchParams.size = params.pageSize;
  }},
  columns: () => [
{chr(10).join(col_lines)}
    {{
      key: 'operate',
      title: $t('common.operate'),
      align: 'center',
      width: 130,
      render: row => (
        <div class="flex-center gap-8px">
          <NButton type="primary" ghost size="small" onClick={{() => edit(row.id)}}>
            {{$t('common.edit')}}
          </NButton>
          <NPopconfirm onPositiveClick={{() => handleDelete(row.id)}}>
            {{{{
              default: () => $t('common.confirmDelete'),
              trigger: () => (
                <NButton type="error" ghost size="small">
                  {{$t('common.delete')}}
                </NButton>
              )
            }}}}
          </NPopconfirm>
        </div>
      )
    }}
  ]
}});

const {{ drawerVisible, operateType, editingData, handleAdd, handleEdit, checkedRowKeys, onBatchDeleted, onDeleted }} =
  useTableOperate(data, 'id', getData);

async function handleBatchDelete() {{
  const {{ error }} = await fetchBatchDelete{entity}({{ ids: checkedRowKeys.value as string[] }});
  if (!error) onBatchDeleted();
}}

async function handleDelete(id: string) {{
  const {{ error }} = await fetchDelete{entity}({{ id }});
  if (!error) onDeleted();
}}

function edit(id: string) {{
  handleEdit(id);
}}
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <{entity}Search v-model:model="searchParams" @search="getDataByPage" />
    <NCard :title="$t('{i18n_page}.pageTitle')" :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <template #header-extra>
        <TableHeaderOperation
          v-model:columns="columnChecks"
          :disabled-delete="checkedRowKeys.length === 0"
          :loading="loading"
          @add="handleAdd"
          @delete="handleBatchDelete"
          @refresh="getData"
        />
      </template>
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :columns="columns"
        :data="data"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="600"
        :loading="loading"
        remote
        :row-key="row => row.id"
        :pagination="mobilePagination"
        class="sm:h-full"
      />
      <{entity}OperateDrawer
        v-model:visible="drawerVisible"
        :operate-type="operateType"
        :row-data="editingData"
        @submitted="getDataByPage"
      />
    </NCard>
  </div>
</template>
"""
    # 规避未使用变量
    _ = search_param_lines
    return template


def gen_view_search(module: str, model: ModelInfo, search_field_names: list[str]) -> str:
    """生成 <entity>-search.vue"""
    entity = model.name
    entity_snake = model.snake_name
    entity_kebab = entity_snake.replace("_", "-")
    ns = snake_to_pascal(module) + "Manage"
    i18n_page = f"page.{module}.{entity_snake}"

    fields = model.schema_fields

    # 生成 form items
    form_items: list[str] = []
    for name in search_field_names:
        f = next((x for x in fields if x.name == name), None)
        if not f:
            continue
        camel = snake_to_camel(name)
        label_key = f"{i18n_page}.{camel}"
        placeholder_key = f"{i18n_page}.form.{camel}"
        component = field_form_component(f)

        item_start = f'            <NFormItemGi span="24 s:12 m:6" :label="$t(\'{label_key}\')" path="{camel}" class="pr-24px">'
        item_end = "            </NFormItemGi>"

        if component in ("input", "textarea"):
            body = f'              <NInput v-model:value="model.{camel}" :placeholder="$t(\'{placeholder_key}\')" />'
        elif component in ("int", "decimal"):
            body = f'              <NInputNumber v-model:value="model.{camel}" :placeholder="$t(\'{placeholder_key}\')" class="w-full" />'
        elif component == "select-status":
            body = f'              <NSelect v-model:value="model.{camel}" :options="statusTypeOptions" clearable :placeholder="$t(\'{placeholder_key}\')" />'
        elif component == "select-todo":
            body = f'              <NSelect v-model:value="model.{camel}" :options="[]" clearable :placeholder="$t(\'{placeholder_key}\')" />'
        else:
            body = f'              <NInput v-model:value="model.{camel}" :placeholder="$t(\'{placeholder_key}\')" />'

        form_items.extend([item_start, body, item_end])

    # 是否引入 statusTypeOptions
    needs_status_import = any((next((x for x in fields if x.name == n), None) or FieldInfo("", "", "")).enum_type == "StatusType" for n in search_field_names)

    imports = [
        "import { toRaw } from 'vue';",
        "import { jsonClone } from '@sa/utils';",
        "import { $t } from '@/locales';",
    ]
    if needs_status_import:
        imports.append("import { statusTypeOptions } from '@/constants/business';")

    template = f"""<script setup lang="ts">
{chr(10).join(imports)}

defineOptions({{ name: '{entity}Search' }});

interface Emits {{
  (e: 'search'): void;
}}

const emit = defineEmits<Emits>();
const model = defineModel<Api.{ns}.{entity}SearchParams>('model', {{ required: true }});
const defaultModel = jsonClone(toRaw(model.value));

function resetModel() {{
  Object.assign(model.value, defaultModel);
}}

function search() {{
  emit('search');
}}
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper">
    <NCollapse :default-expanded-names="['{entity_kebab}-search']">
      <NCollapseItem :title="$t('common.search')" name="{entity_kebab}-search">
        <NForm :model="model" label-placement="left" :label-width="80">
          <NGrid responsive="screen" item-responsive>
{chr(10).join(form_items)}
            <NFormItemGi span="24 s:12 m:6">
              <NSpace class="w-full" justify="end">
                <NButton @click="resetModel">
                  <template #icon><icon-ic-round-refresh class="text-icon" /></template>
                  {{{{ $t('common.reset') }}}}
                </NButton>
                <NButton type="primary" ghost @click="search">
                  <template #icon><icon-ic-round-search class="text-icon" /></template>
                  {{{{ $t('common.search') }}}}
                </NButton>
              </NSpace>
            </NFormItemGi>
          </NGrid>
        </NForm>
      </NCollapseItem>
    </NCollapse>
  </NCard>
</template>
"""
    return template


def gen_view_drawer(module: str, model: ModelInfo) -> str:
    """生成 <entity>-operate-drawer.vue"""
    entity = model.name
    entity_snake = model.snake_name
    ns = snake_to_pascal(module) + "Manage"
    i18n_page = f"page.{module}.{entity_snake}"

    fields = model.schema_fields
    fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

    # 生成 form items
    form_items: list[str] = []
    for f in fields:
        form_items.extend(_form_item_block(f, i18n_page, is_relation=False))
    for r in fk_relations:
        form_items.extend(_form_item_block(r, i18n_page, is_relation=True))

    # 默认 model
    default_entries: list[str] = []
    for f in fields:
        camel = snake_to_camel(f.name)
        default_entries.append(f"    {camel}: {_default_value_for_field(f)}")
    for r in fk_relations:
        camel = snake_to_camel(r.name) + "Id"
        default_entries.append(f"    {camel}: null")

    # 必填规则
    required_rules: list[str] = []
    for f in fields:
        if f.required:
            camel = snake_to_camel(f.name)
            required_rules.append(f"  {camel}: defaultRequiredRule")
    for r in fk_relations:
        if not r.nullable:
            camel = snake_to_camel(r.name) + "Id"
            required_rules.append(f"  {camel}: defaultRequiredRule")

    # 是否需要 statusTypeOptions
    needs_status_import = any(f.enum_type == "StatusType" for f in fields)

    extra_imports: list[str] = []
    if needs_status_import:
        extra_imports.append("import { statusTypeOptions } from '@/constants/business';")

    entity_title_key = f"{i18n_page}.pageTitle"
    add_key = f"{i18n_page}.add{entity}"
    edit_key = f"{i18n_page}.edit{entity}"

    template = f"""<script setup lang="ts">
import {{ computed, ref, watch }} from 'vue';
import {{ jsonClone }} from '@sa/utils';
import {{ fetchAdd{entity}, fetchUpdate{entity} }} from '@/service/api';
import {{ useFormRules, useNaiveForm }} from '@/hooks/common/form';
import {{ $t }} from '@/locales';
{chr(10).join(extra_imports)}

defineOptions({{ name: '{entity}OperateDrawer' }});

interface Props {{
  operateType: NaiveUI.TableOperateType;
  rowData?: Api.{ns}.{entity} | null;
}}

const props = defineProps<Props>();

interface Emits {{
  (e: 'submitted'): void;
}}

const emit = defineEmits<Emits>();
const visible = defineModel<boolean>('visible', {{ default: false }});
const {{ formRef, validate, restoreValidation }} = useNaiveForm();
const {{ defaultRequiredRule }} = useFormRules();

const title = computed(() => {{
  const titles: Record<NaiveUI.TableOperateType, string> = {{
    add: $t('{add_key}'),
    edit: $t('{edit_key}')
  }};
  return titles[props.operateType];
}});

const model = ref(createDefaultModel());

function createDefaultModel(): Api.{ns}.{entity}AddParams {{
  return {{
{("," + chr(10)).join(default_entries)}
  }} as unknown as Api.{ns}.{entity}AddParams;
}}

const rules: Record<string, App.Global.FormRule> = {{
{("," + chr(10)).join(required_rules)}
}};

function handleInitModel() {{
  model.value = createDefaultModel();
  if (props.operateType === 'edit' && props.rowData) {{
    Object.assign(model.value, jsonClone(props.rowData));
  }}
}}

function closeDrawer() {{
  visible.value = false;
}}

async function handleSubmit() {{
  await validate();
  if (props.operateType === 'add') {{
    const {{ error }} = await fetchAdd{entity}(model.value);
    if (error) return;
    window.$message?.success($t('common.addSuccess'));
  }} else {{
    const {{ error }} = await fetchUpdate{entity}({{ id: props.rowData?.id, ...model.value }});
    if (error) return;
    window.$message?.success($t('common.updateSuccess'));
  }}
  closeDrawer();
  emit('submitted');
}}

watch(visible, () => {{
  if (visible.value) {{
    handleInitModel();
    restoreValidation();
  }}
}});
</script>

<template>
  <NDrawer v-model:show="visible" display-directive="show" :width="420">
    <NDrawerContent :title="title" :native-scrollbar="false" closable>
      <NForm ref="formRef" :model="model" :rules="rules">
{chr(10).join(form_items)}
      </NForm>
      <template #footer>
        <NSpace :size="16">
          <NButton @click="closeDrawer">{{{{ $t('common.cancel') }}}}</NButton>
          <NButton type="primary" @click="handleSubmit">{{{{ $t('common.confirm') }}}}</NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>
"""
    # 规避未使用变量
    _ = entity_title_key
    return template


# ─── i18n 片段 ───


def gen_i18n_zh(module: str, module_cn: str, models: list[ModelInfo]) -> str:
    """生成 zh-cn 片段 — markdown 格式，从 description 提取。"""
    lines = [
        f"# zh-cn 合并片段（模块：{module_cn}）",
        "",
        "将下面两个代码块对应合并到 `web/src/locales/langs/zh-cn.ts`。",
        "",
        "## 1. `route` 对象追加",
        "",
        "```ts",
        f"{module}: '{module_cn}',",
    ]
    for model in models:
        lines.append(f"{module}_{model.snake_name}: '{model.cn_name}',")
    lines.append("```")
    lines.append("")
    lines.append("## 2. `page` 对象追加")
    lines.append("")
    lines.append("```ts")
    lines.append(f"{module}: {{")
    lines.append("  common: { status: '状态', form: { status: '请选择状态' } },")
    for model in models:
        entity_snake = model.snake_name
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"  {entity_snake}: {{")
        lines.append(f"    pageTitle: '{model.cn_name}',")
        for f in fields:
            camel = snake_to_camel(f.name)
            title = cn_title(f.description, f.name)
            lines.append(f"    {camel}: '{title}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            if r.description:
                lines.append(f"    {camel}: '{cn_title(r.description, r.name)}',")
            else:
                lines.append(f"    {camel}: '{camel}',  // TODO: 手动填写中文")
        lines.append("    form: {")
        for f in fields:
            camel = snake_to_camel(f.name)
            title = cn_title(f.description, f.name)
            verb = "请选择" if field_form_component(f).startswith("select") else "请输入"
            lines.append(f"      {camel}: '{verb}{title}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            if r.description:
                lines.append(f"      {camel}: '请选择{cn_title(r.description, r.name)}',")
            else:
                lines.append(f"      {camel}: '请选择{camel}',  // TODO")
        lines.append("    },")
        lines.append(f"    add{model.name}: '新增{model.cn_name}',")
        lines.append(f"    edit{model.name}: '编辑{model.cn_name}'")
        lines.append("  },")
    lines.append("}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def gen_i18n_en(module: str, models: list[ModelInfo]) -> str:
    """生成 en-us 片段 — markdown 格式，fallback 为字段名 camelCase。"""
    module_pascal = snake_to_pascal(module)
    lines = [
        f"# en-us merge snippet (module: {module_pascal})",
        "",
        "Merge both blocks below into `web/src/locales/langs/en-us.ts`.",
        "",
        "## 1. Append to `route` object",
        "",
        "```ts",
        f"{module}: '{module_pascal}',",
    ]
    for model in models:
        name_title = re.sub(r"(?<!^)(?=[A-Z])", " ", model.name).strip()
        lines.append(f"{module}_{model.snake_name}: '{name_title}',")
    lines.append("```")
    lines.append("")
    lines.append("## 2. Append to `page` object")
    lines.append("")
    lines.append("```ts")
    lines.append(f"{module}: {{")
    lines.append("  common: { status: 'Status', form: { status: 'Please select status' } },")
    for model in models:
        entity_snake = model.snake_name
        entity_en = re.sub(r"(?<!^)(?=[A-Z])", " ", model.name).strip()
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"  {entity_snake}: {{")
        lines.append(f"    pageTitle: '{entity_en}',")
        for f in fields:
            camel = snake_to_camel(f.name)
            lines.append(f"    {camel}: '{camel}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            lines.append(f"    {camel}: '{camel}',")
        lines.append("    form: {")
        for f in fields:
            camel = snake_to_camel(f.name)
            verb = "Please select" if field_form_component(f).startswith("select") else "Please input"
            lines.append(f"      {camel}: '{verb} {camel}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            lines.append(f"      {camel}: 'Please select {camel}',")
        lines.append("    },")
        lines.append(f"    add{model.name}: 'Add {entity_en}',")
        lines.append(f"    edit{model.name}: 'Edit {entity_en}'")
        lines.append("  },")
    lines.append("}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def gen_i18n_schema_dts(module: str, models: list[ModelInfo]) -> str:
    """生成 App.I18n.Schema.page.<module> 扩展片段 — markdown。

    Schema 是强类型 type，未扩展时 $t('page.<module>...') 会在 vue-tsc 里报
    "is not assignable to parameter of type 'I18nKey'"。
    """
    lines = [
        f"# `App.I18n.Schema.page` 扩展片段（模块：{module}）",
        "",
        "将下面代码块合并到 `web/src/typings/app.d.ts` 里 `App.I18n.Schema.page` 对象中",
        "（靠近其它模块条目，例如 `hr: {...}` 之后）。",
        "",
        "没有这一步，生成的视图里 `$t('page.<module>.<entity>.xxx')` 会编译报错:",
        "`is not assignable to parameter of type 'I18nKey'`。",
        "",
        "```ts",
        f"{module}: {{",
        "  common: {",
        "    status: string;",
        "    form: { status: string };",
        "  };",
    ]
    for model in models:
        entity_snake = model.snake_name
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"  {entity_snake}: {{")
        lines.append("    pageTitle: string;")
        for f in fields:
            lines.append(f"    {snake_to_camel(f.name)}: string;")
        for r in fk_relations:
            lines.append(f"    {snake_to_camel(r.name)}: string;")
        lines.append("    form: {")
        for f in fields:
            lines.append(f"      {snake_to_camel(f.name)}: string;")
        for r in fk_relations:
            lines.append(f"      {snake_to_camel(r.name)}: string;")
        lines.append("    };")
        lines.append(f"    add{model.name}: string;")
        lines.append(f"    edit{model.name}: string;")
        lines.append("  };")
    lines.append("};")
    lines.append("```")
    lines.append("")
    lines.append("此外，`App.I18n.Schema.route` 使用 `Record<I18nRouteKey, string>`，")
    lines.append("`I18nRouteKey` 由 Elegant Router 从 `web/src/views/` 目录自动推导 ——")
    lines.append("只要 `pnpm dev` 启动过一次，`web/src/typings/elegant-router.d.ts` 会自动更新，无需手动改。")
    lines.append("")
    return "\n".join(lines)


# ─── 幂等追加 service/api/index.ts ───


def append_to_index_ts(web_root: Path, module: str) -> str:
    """向 service/api/index.ts 追加 export，已存在则跳过。返回状态。"""
    index_path = web_root / "src" / "service" / "api" / "index.ts"
    if not index_path.exists():
        return "not-found"

    content = index_path.read_text(encoding="utf-8")
    export_line = f"export * from './{module}-manage';"
    if export_line in content:
        return "exists"

    new_content = content.rstrip() + "\n" + export_line + "\n"
    index_path.write_text(new_content, encoding="utf-8")
    return "appended"


# ─── 汇总生成 ───


def generate_web(
    web_root: Path,
    module: str,
    module_cn: str,
    models: list[ModelInfo],
    *,
    list_fields_map: dict[str, list[str]],
    search_fields_map: dict[str, list[str]],
    force: bool = False,
) -> list[tuple[str, str]]:
    """生成前端所有文件，返回 [(相对路径, 状态)] 列表。"""
    results: list[tuple[str, str]] = []

    def write(path: Path, content: str) -> None:
        rel = str(path.relative_to(web_root))
        if path.exists() and not force:
            results.append((rel, "exists"))
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        results.append((rel, "created"))

    # service ts
    write(
        web_root / "src" / "service" / "api" / f"{module}-manage.ts",
        gen_service_ts(module, models),
    )

    # typings d.ts
    write(
        web_root / "src" / "typings" / "api" / f"{module}-manage.d.ts",
        gen_typings_dts(module, models, search_fields_map),
    )

    # views
    for model in models:
        entity_kebab = model.snake_name.replace("_", "-")
        view_dir = web_root / "src" / "views" / module / entity_kebab

        list_fields = list_fields_map.get(model.name, [f.name for f in model.schema_fields[:5]])
        search_fields = search_fields_map.get(model.name, [])

        write(view_dir / "index.vue", gen_view_index(module, model, list_fields))
        write(view_dir / "modules" / f"{entity_kebab}-search.vue", gen_view_search(module, model, search_fields))
        write(view_dir / "modules" / f"{entity_kebab}-operate-drawer.vue", gen_view_drawer(module, model))

    # i18n 片段
    # i18n 片段 — .md 避免被 oxlint/eslint 当 TS 源码扫描
    i18n_dir = web_root / "src" / "locales" / "langs" / "_generated" / module
    write(i18n_dir / "zh-cn.md", gen_i18n_zh(module, module_cn, models))
    write(i18n_dir / "en-us.md", gen_i18n_en(module, models))
    write(i18n_dir / "app.d.ts.md", gen_i18n_schema_dts(module, models))

    # 追加 index.ts
    status = append_to_index_ts(web_root, module)
    results.append(("src/service/api/index.ts", status))

    return results
