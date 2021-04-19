<p align="center">
    <a href="https://www.odoo.com/documentation/12.0/index.html">
        <img alt="odoo version" src="https://img.shields.io/badge/odoo-version%2012-875A7B.svg?style=flat"></img>
    </a>
    <a href="http://www.alliantum.com">
        <img alt="company" src="https://img.shields.io/badge/company-Alliantum-blue.svg?style=flat"></img>
    </a>
    <a href="http://www.gnu.org/licenses/agpl-3.0-standalone.html">
        <img alt="license" src="https://img.shields.io/badge/license-AGPL--3-blue.svg?style=flat"></img>
    </a>
    <a href="https://github.com/{user_name}/{repo_name}/releases/latest">
        <img src="https://img.shields.io/badge/module%20version-1.0.0-F47D42.svg?style=plastic&"></img>
    </a>
</p>

<div align="center">
    <a href="http://www.alliantum.com">
        <img src="./static/description/icon.png" width="10%">
    </a>
    <div>
        <h1>MO Max. Amount</h1>
        Sets a maximum quantity for each product that can be manufactured on single Manufacturing Order.
        <hr>
    </div>
</div>

## Installation

This module depends on `mrp_production_grouped_by_product`. You can find it at [OCA/mrp_production_grouped_by_product](https://github.com/OCA/manufacture/tree/12.0/mrp_production_grouped_by_product)

- This will be the new field in the product view (both product and variants)
    <div align="center">
        <img src="./static/description/screenshot1.png" width="90%"  style="border-radius: 5px;">
    </div>

## Usage

Install this add-on and it will be automatically ready to use.
In order to trigger the blocking warning functionality you only need to create a Manufacture Order with more units than what is in the "Maximum per MO" field on the product
    <div align="center">
        <img src="./static/description/screenshot2.png" width="70%"  style="border-radius: 5px;">
    </div>
## Contributors

- [Alliantum](http://www.alliantum.com)
