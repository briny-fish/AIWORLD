local modname = minetest.get_current_modname()
local modpath = minetest.get_modpath(modname)
local placed = false

local materials = {
  ["aiworld_bridge:location_civic"] = {desc = "AIWORLD Civic Location", color = "#5b7f78"},
  ["aiworld_bridge:location_dwelling"] = {desc = "AIWORLD Dwelling", color = "#6aa3d8"},
  ["aiworld_bridge:location_farm"] = {desc = "AIWORLD Farm", color = "#4f8f5f"},
  ["aiworld_bridge:location_production"] = {desc = "AIWORLD Workshop", color = "#d49b4a"},
  ["aiworld_bridge:location_wildland"] = {desc = "AIWORLD Wildland", color = "#6f8c56"},
  ["aiworld_bridge:location_damaged"] = {desc = "AIWORLD Damaged Location", color = "#a33232"},
  ["aiworld_bridge:route_open"] = {desc = "AIWORLD Route", color = "#436f76"},
  ["aiworld_bridge:route_blocked"] = {desc = "AIWORLD Blocked Route", color = "#a33232"},
  ["aiworld_bridge:organization"] = {desc = "AIWORLD Organization", color = "#6aa3d8"},
  ["aiworld_bridge:organization_fractured"] = {desc = "AIWORLD Fractured Organization", color = "#d16d6d"},
}

for node_name, spec in pairs(materials) do
  minetest.register_node(node_name, {
    description = spec.desc,
    tiles = {"default_stone.png^[colorize:" .. spec.color .. ":170"},
    groups = {cracky = 3, oddly_breakable_by_hand = 2},
    paramtype = "light",
    sunlight_propagates = true,
  })
end

minetest.register_entity("aiworld_bridge:agent_marker", {
  initial_properties = {
    physical = false,
    pointable = true,
    visual = "cube",
    visual_size = {x = 0.45, y = 1.0},
    textures = {
      "default_wood.png^[colorize:#eef5f2:160",
      "default_wood.png^[colorize:#eef5f2:160",
      "default_wood.png^[colorize:#eef5f2:160",
      "default_wood.png^[colorize:#eef5f2:160",
      "default_wood.png^[colorize:#eef5f2:160",
      "default_wood.png^[colorize:#eef5f2:160",
    },
    nametag = "AIWORLD agent",
    nametag_color = "#eef5f2",
  },

  on_activate = function(self, staticdata)
    local data = minetest.deserialize(staticdata or "") or {}
    self.aiworld = data
    self.object:set_nametag_attributes({
      text = data.name or "AIWORLD agent",
      color = data.color or "#eef5f2",
    })
    self.object:set_properties({
      textures = {
        "default_wood.png^[colorize:" .. (data.color or "#eef5f2") .. ":160",
        "default_wood.png^[colorize:" .. (data.color or "#eef5f2") .. ":160",
        "default_wood.png^[colorize:" .. (data.color or "#eef5f2") .. ":160",
        "default_wood.png^[colorize:" .. (data.color or "#eef5f2") .. ":160",
        "default_wood.png^[colorize:" .. (data.color or "#eef5f2") .. ":160",
        "default_wood.png^[colorize:" .. (data.color or "#eef5f2") .. ":160",
      },
    })
  end,

  get_staticdata = function(self)
    return minetest.serialize(self.aiworld or {})
  end,
})

local function read_scene()
  local file = io.open(modpath .. "/scene.json", "r")
  if not file then
    minetest.log("warning", "[aiworld_bridge] scene.json not found")
    return nil
  end
  local text = file:read("*a")
  file:close()
  local scene = minetest.parse_json(text)
  if not scene then
    minetest.log("error", "[aiworld_bridge] failed to parse scene.json")
  end
  return scene
end

local function place_scene(scene)
  for _, item in ipairs(scene.nodes or {}) do
    if item.pos and item.node then
      minetest.set_node(item.pos, {name = item.node})
    end
  end

  for _, agent in ipairs(scene.entities or {}) do
    if agent.pos then
      local object = minetest.add_entity(agent.pos, "aiworld_bridge:agent_marker", minetest.serialize(agent))
      if object then
        object:set_nametag_attributes({
          text = agent.name or agent.id or "AIWORLD agent",
          color = agent.color or "#eef5f2",
        })
      end
    end
  end

  minetest.chat_send_all("[AIWORLD] loaded day " .. tostring((scene.source or {}).day or "?") .. " static society scene")
  for _, entry in ipairs(scene.social_log or {}) do
    minetest.chat_send_all("[AIWORLD day " .. tostring(entry.day or "?") .. "] " .. tostring(entry.summary or entry.title or "social event"))
  end
end

minetest.register_on_joinplayer(function(player)
  if placed then
    return
  end
  placed = true
  minetest.after(1.0, function()
    local scene = read_scene()
    if scene then
      place_scene(scene)
    end
  end)
end)
