const mongoose = require('mongoose');
const productSchema = new mongoose.Schema({
  name: String,
  price: Number,
  image: String,
  description: String,
  category: String,
  store: String
}, { timestamps: true });
module.exports = mongoose.model('Product', productSchema);
