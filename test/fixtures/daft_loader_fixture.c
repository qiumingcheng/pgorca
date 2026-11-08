/* Incompatible native fixtures: never used as an execution runtime. */
#include "daft_pg_bridge.h"

uint32_t dpg_abi_major(void)
{
#ifdef MISSING_SYMBOL_FIXTURE
    return DPG_ABI_MAJOR;
#else
    return DPG_ABI_MAJOR + 1;
#endif
}

#ifndef MISSING_SYMBOL_FIXTURE
uint32_t dpg_abi_minor(void) { return DPG_ABI_MINOR; }
uint64_t dpg_capabilities(void) { return 0; }
dpg_status dpg_capability_digest_v1(uint8_t out[DPG_CAPABILITY_DIGEST_BYTES])
{ return DPG_INCOMPATIBLE; }
dpg_status dpg_open_v1(const uint8_t *plan, uint64_t len,
                       const dpg_config_v1 *config, dpg_handle **out, dpg_error **err)
{ return DPG_INCOMPATIBLE; }
dpg_status dpg_try_push_batch_v1(dpg_handle *handle, uint32_t source,
                                struct ArrowArray *array, struct ArrowSchema *schema,
                                dpg_error **err)
{ return DPG_INCOMPATIBLE; }
dpg_status dpg_finish_source_v1(dpg_handle *handle, uint32_t source, dpg_error **err)
{ return DPG_INCOMPATIBLE; }
dpg_status dpg_try_next_batch_v1(dpg_handle *handle, struct ArrowArray *array,
                                struct ArrowSchema *schema, dpg_error **err)
{ return DPG_INCOMPATIBLE; }
dpg_status dpg_wait_v1(dpg_handle *handle, uint32_t timeout, uint64_t *events, dpg_error **err)
{ return DPG_INCOMPATIBLE; }
dpg_status dpg_metrics_snapshot_v1(dpg_handle *handle, dpg_metrics_v1 *out, dpg_error **err)
{ return DPG_INCOMPATIBLE; }
void dpg_cancel_v1(dpg_handle *handle) {}
void dpg_close_v1(dpg_handle **handle) {}
const char *dpg_error_message_v1(const dpg_error *err) { return "incompatible test fixture"; }
void dpg_error_free_v1(dpg_error **err) {}
#endif
